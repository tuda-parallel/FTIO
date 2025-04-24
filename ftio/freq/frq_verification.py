
import matplotlib.pyplot as plt  
import numpy as np

from scipy.stats import pearsonr, spearmanr

# pearson correllation coefficient
def pcc(signal, test):
    if len(signal) < len(test):
        length = len(signal)
    else:
        length = len(test)

    coeff, = pearsonr(signal[:length], test[:length])

    return coeff

# spearman correlation coeffient
def scc(signal, test):
    if len(signal) < len(test):
        length = len(signal)
    else:
        length = len(test)

    res = spearmanr(signal[:length], test[:length])

    return res




