
import matplotlib.pyplot as plt  
import numpy as np

from scipy.stats import pearsonr, spearmanr

# pearson correlation coefficient
def pcc(signal, test):
    if len(signal) < len(test):
        length = len(signal)
    else:
        length = len(test)

    res = pearsonr(signal[:length], test[:length])

    return res

# spearman correlation coeffient
def scc(signal, test):
    if len(signal) < len(test):
        length = len(signal)
    else:
        length = len(test)

    res = spearmanr(signal[:length], test[:length])

    return res




