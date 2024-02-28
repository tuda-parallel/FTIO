import numpy as np
from ftio.parse.overlap_thread import overlap_thread
from numba import jit


class Bandwidth:
    """this class contains the bandwidth + time metrics at the
        different levels:
        1) request level: subscripted ind (for individual requests)
    _ovr
        2) Rank level metrics: avrerage (avr) or sum. Represent either the
        sum/avr of the ind level metrics during a phase.

        3) Application level metrics:  subscripted overlap. Calculated by
        overlapping the previous metrics. The most accurate one is ind, however,
        it has the higest overhead.
    """

    def __init__(self, b, io_type, args):  # b = values["bandwidth"]
        # App level
        self.b_overlap_sum = []
        self.b_overlap_avr = []
        self.t_overlap = []
        self.b_overlap_ind = []
        self.t_overlap_ind = []
        # Rank level
        self.b_rank_sum = []
        self.b_rank_avr = []
        self.t_rank_s = []
        self.t_rank_e = []
        # Ind level
        self.b_ind = []
        self.t_ind_s = []
        self.t_ind_e = []

        # Application level metrics
        # if "n_overlap" in b:
        # 	self.n_overlap.extend(b["n_overlap"])
        if "b_overlap_sum" in b:
            self.b_overlap_sum.extend(b["b_overlap_sum"])
        if "b_overlap_avr" in b:
            self.b_overlap_avr.extend(b["b_overlap_avr"])
        if "t_overlap" in b:
            self.t_overlap.extend(b["t_overlap"])
        else:
            if "b_overlap_sum" in b:
                self.t_overlap.extend(np.zeros(len(b["b_overlap_sum"])))
            elif "b_overlap_avr" in b:
                self.t_overlap.extend(np.zeros(len(b["b_overlap_avr"])))

        # Rank level metrics
        # remove later
        # ---------------------------------
        if "b" in b and "async" in io_type:
            print("Compatibility mode")
            self.b_rank_sum.extend(b["b"])
            self.b_rank_avr.extend(np.zeros(len(b["b"])))
            self.t_rank_s.extend(np.zeros(len(b["b"])))
            self.t_rank_e.extend(np.zeros(len(b["b"])))
        elif "b" in b and "sync" in io_type:
            print("Compatibility mode")
            self.b_rank_avr.extend(b["b"])
            self.b_rank_sum.extend(np.zeros(len(b["b"])))
            self.t_rank_s.extend(np.zeros(len(b["b"])))
            self.t_rank_e.extend(np.zeros(len(b["b"])))
        # ---------------------------------

        if args.avr or args.sum:
            # 1) assign rank level metric
            if args.sum:
                if "b_rank_sum" in b:
                    self.b_rank_sum.extend(b["b_rank_sum"])

            if args.avr:
                if "b_rank_avr" in b:
                    self.b_rank_avr.extend(b["b_rank_avr"])

            if "t_rank_s" in b:
                self.t_rank_s.extend(b["t_rank_s"])
                if "t_rank_e" in b and b["t_rank_e"]:
                    self.t_rank_e.extend(b["t_rank_e"])
                else:
                    if b["t_rank_s"]:
                        self.t_rank_e.extend(b["t_rank_s"][1:])
                        self.t_rank_e.append(b["t_rank_s"][-1])
                        b["t_rank_e"] = self.t_rank_e
                    else:
                        pass
            else:
                if "b_rank_sum" in b:
                    self.t_rank_s.extend(np.zeros(len(b["b_rank_sum"])))
                    self.t_rank_e.extend(np.zeros(len(b["b_rank_sum"])))
                elif "b_rank_avr" in b:
                    self.t_rank_s.extend(np.zeros(len(b["b_rank_avr"])))
                    self.t_rank_e.extend(np.zeros(len(b["b_rank_avr"])))

            # 2) Calcluate bandwidth overlapping at rank level
            if ("t_rank_s" in b) and "b_overlap_avr" not in b and args.avr:
                self.b_overlap_avr, self.t_overlap = overlap(
                    b["b_rank_avr"], b["t_rank_s"], b["t_rank_e"]
                )
            if ("t_rank_s" in b) and "b_overlap_sum" not in b and args.sum:
                self.b_overlap_sum, self.t_overlap = overlap(
                    b["b_rank_sum"], b["t_rank_s"], b["t_rank_e"]
                )

        # overlapping thread level
        if args.ind:
            # Thread level metrics
            if "b_ind" in b:
                self.b_ind.extend(b["b_ind"])
                #! overlap ind
                self.b_overlap_ind, self.t_overlap_ind = overlap(
                    b["b_ind"], b["t_ind_s"], b["t_ind_e"]
                )

            if "t_ind_s" in b:
                self.t_ind_s.extend(b["t_ind_s"])

            if "t_ind_e" in b:
                self.t_ind_e.extend(b["t_ind_e"])

        self.app_ind = max(self.b_overlap_ind) if self.b_overlap_ind else -1
        self.app_avr = max(self.b_overlap_avr) if self.b_overlap_avr else -1
        self.app_sum = max(self.b_overlap_sum) if self.b_overlap_sum else -1

        # statistics:
        self.weighted_harmonic_mean = self.assign(b, "weighted_harmonic_mean")
        self.harmonic_mean = self.assign(b, "harmonic_mean")
        self.arithmetic_mean = self.assign(b, "arithmetic_mean")
        self.median = self.assign(b, "median")
        self.max = self.assign(b, "max")
        self.min = self.assign(b, "min")

        self.weighted_avr_harmonic_mean = self.assign(b, "weighted_avr_harmonic_mean")
        self.harmonic_avr_mean = self.assign(b, "harmonic_avr_mean")
        self.arithmetic_avr_mean = self.assign(b, "arithmetic_avr_mean")
        self.median_avr = self.assign(b, "median_avr")
        self.max_avr = self.assign(b, "max_avr")
        self.min_avr = self.assign(b, "min_avr")

        self.weighted_sum_harmonic_mean = self.assign(b, "weighted_sum_harmonic_mean")
        self.harmonic_sum_mean = self.assign(b, "harmonic_sum_mean")
        self.arithmetic_sum_mean = self.assign(b, "arithmetic_sum_mean")
        self.median_sum = self.assign(b, "median_sum")
        self.max_sum = self.assign(b, "max_sum")
        self.min_sum = self.assign(b, "min_sum")

    def assign(self, b, name):
        if name in b:
            return b[name] if not np.isnan(b[name]) else -1
        else:
            return -1


#! ----------------------- I/O anaylsis ------------------------------
# **********************************************************************
# *                       1. Overlap
# **********************************************************************


def overlap(b, t_s, t_e):
    t_s = np.array(t_s)
    t_e = np.array(t_e)
    b = np.array(b)
    id_s = np.argsort(t_s)
    id_e = np.argsort(t_e)
    try:
        b_ovrlap, t_ovrlap = overlap_core(b, t_s, t_e, id_s, id_e)
    except:
        b_ovrlap, t_ovrlap = overlap_core_safe(b, t_s, t_e, id_s, id_e)
    return list(b_ovrlap), list(t_ovrlap)


@jit(nopython=True, cache=True)
def overlap_core(b, t_s, t_e, id_s, id_e):
    agg_phases = len(t_s)

    b_out = np.zeros(2 * agg_phases)
    t_out = np.zeros(2 * agg_phases)

    b_tmp = 0
    k_s = 0
    k_e = 0
    counter = 0

    while k_s < agg_phases or k_e < agg_phases:
        if k_s == agg_phases or t_e[id_e[k_e]] < t_s[id_s[k_s]]:
            b_tmp = b_tmp - b[id_e[k_e]]
            # t_out.append(t_e[id_e[k_e]])
            t_out[counter] = t_e[id_e[k_e]]
            k_e += 1
        else:
            b_tmp = b_tmp + b[id_s[k_s]]
            # t_out.append(t_s[id_s[k_s]])
            t_out[counter] = t_s[id_s[k_s]]
            k_s += 1
        # b_out.append(b_tmp)
        b_out[counter] = b_tmp
        counter += 1

    return b_out, t_out


def overlap_core_safe(b, t_s, t_e, id_s, id_e):
    agg_phases = len(t_s)

    b_out = []
    t_out = []
    b_tmp = 0
    k_s = 0
    k_e = 0

    while k_s < agg_phases or k_e < agg_phases:
        if k_s == agg_phases or t_e[id_e[k_e]] < t_s[id_s[k_s]]:
            b_tmp = b_tmp - b[id_e[k_e]]
            t_out.append(t_e[id_e[k_e]])
            k_e += 1
        else:
            b_tmp = b_tmp + b[id_s[k_s]]
            t_out.append(t_s[id_s[k_s]])
            k_s += 1
        b_out.append(b_tmp)

    return b_out, t_out
