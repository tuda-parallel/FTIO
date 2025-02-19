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
from ftio.freq.anomaly_detection import z_score

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

# https://www.geeksforgeeks.org/python-opencv-connected-component-labeling-and-analysis/
def component_linking(image):

    frame = np.array(image, dtype="uint8")

    analysis = cv2.connectedComponentsWithStats(frame, 8, cv2.CV_32S)
    (totalLabels, label_ids, values, centroid) = analysis

    output = np.zeros(image.shape, dtype="uint8")

    # Loop through each component
    for i in range(1, totalLabels):
        # Area of the component
        area = values[i, cv2.CC_STAT_AREA]

        if (area > 80):
            componentMask = (label_ids == i).astype("uint8") * 255
            output = cv2.bitwise_or(output, componentMask)

    cv2.imshow("Image", frame)
    cv2.imshow("Filtered Components", output)
    cv2.waitKey(15000)
