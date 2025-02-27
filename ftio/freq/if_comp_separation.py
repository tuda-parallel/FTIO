"""
TODO:
binary image:
- denoise signal (preprocessing?)
- adjust prominence threshold
component_linking:
- set area threshold depending on sampling frequency and minimum win size
  (shortest relevant I/O phase period?)
- 10-connected neighbouring set
"""

import cv2
import numpy as np
from scipy.signal import find_peaks, peak_prominences
from ftio.freq.anomaly_detection import z_score, remove_harmonics

"""
Rankine, L., Mesbah, M., & Boashash, B. (2007).
IF estimation for multicomponent signals using image processing
techniques in the time-frequency domain.
Signal Processing, 87(6), 1234-1250.
"""
def binary_image(Zxx):
    bin_im = np.zeros_like(Zxx, dtype="uint8")
    rows = np.shape(Zxx)[0]

    for i in range(0,rows):
        freqs = np.abs(Zxx[i])
        peaks = find_peaks(freqs)

        prom = peak_prominences(freqs, peaks[0])[0]

        if(prom.size > 0):
            for ind in range(0,len(prom)):
                if prom[ind] > 0.01:
                    _ind = peaks[0][ind]
                    bin_im[i][_ind] = 255

    return bin_im

def binary_image_nprom(Zxx):
    bin_im = np.zeros_like(Zxx, dtype="uint8")
    rows = np.shape(Zxx)[0]

    for i in range(0,rows):
        freqs = np.abs(Zxx[i])
        peaks = find_peaks(freqs)

        prom = peak_prominences(freqs, peaks[0])[0]
        prom_sorted = np.argsort(prom)

        prom_filtered = []
        if (len(peaks[0]) > 3):
            prom_filtered.append(prom[prom_sorted[-1]])
            prom_filtered.append(prom[prom_sorted[-2]])
            prom_filtered.append(prom[prom_sorted[-3]])
        else:
            prom_filtered = prom

        if(len(prom_filtered) > 0):
            for ind in range(0,len(prom_filtered)):
                if prom_filtered[ind] > 0.1:
                    _ind = peaks[0][ind]
                    bin_im[i][_ind] = 255

    return bin_im

def binary_image_zscore(Zxx, freq, args):
    bin_im = np.zeros_like(Zxx, dtype="uint8")
    rows = np.shape(Zxx)[0]

    for i in range(0,rows):
        yf = np.abs(Zxx[i])
        n = len(yf)
        freq_arr = freq * np.arange(0, n) / n
        indices = z_score(yf, freq_arr, args)[0]

        for ind in indices:
            bin_im[i][ind] = 255

    return bin_im

def binary_image_zscore_extended(Zxx, freq, args):
    bin_im = np.zeros_like(Zxx, dtype="uint8")
    rows = np.shape(Zxx)[0]

    zscore_freq = []

    for i in range(0,rows):
        freqs = np.abs(Zxx[i])
        peaks_ = find_peaks(freqs)

        n = len(freqs)
        freq_arr = freq * np.arange(0, n) / n
        indices = z_score(freqs, freq_arr, args)[0]

        peaks = remove_harmonics(freq_arr, freq_arr, peaks_[0])[0]
        prom = peak_prominences(freqs, peaks)[0]

        for ind in indices:
            if not ind in zscore_freq:
                zscore_freq.append(ind)
                zscore_freq.append(ind-1)
                zscore_freq.append(ind+1)

        if(prom.size > 0):
            for ind in range(0,len(prom)):
                if prom[ind] > 0.01:
                    #_ind = peaks[0][ind]
                    _ind = peaks[ind]
                    if _ind in zscore_freq:
                        bin_im[i][_ind] = 255

    return bin_im

# https://www.geeksforgeeks.org/python-opencv-connected-component-labeling-and-analysis/
def component_linking(image):

    frame = np.array(image, dtype="uint8")

    analysis = cv2.connectedComponentsWithStats(frame, 8, cv2.CV_32S)
    (totalLabels, label_ids, values, centroid) = analysis

    output = np.zeros(image.shape, dtype="uint8")

    components = []

    # Loop through each component
    for i in range(1, totalLabels):
        # Area of the component
        area = values[i, cv2.CC_STAT_AREA]

        if (area > 80):
            componentMask = (label_ids == i).astype("uint8") * 255
            output = cv2.bitwise_or(output, componentMask)

            components.append(i)

    result = []
    for i in components:
        indices, freqs = np.where(label_ids == i)

        start = indices[0]
        end = indices[-1]
        time = start, end

        comp = time, freqs
        result.append(comp)

    #filename = "cv2_image.jpg"
    #cv2.imwrite(filename, frame)
    #filename = "cv2_filtered.jpg"
    #cv2.imwrite(filename, output)

    cv2.imshow("Image", frame)
    cv2.imshow("Filtered Components", output)
    cv2.waitKey(15000)

    return result
