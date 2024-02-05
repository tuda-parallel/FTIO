""" Wavlet functions (continous and discrete) + plot methods
    """
import numpy as np
import pywt
from scipy import signal
import matplotlib.pyplot as plt

# Wavelet
# ----------
def wavelet_cont(b_sampled, wavelet, level, freq):
    # Continouse wavelet:
    n = len(b_sampled)
    if isinstance(level, str) and "auto" in level:
        level = pywt.dwt_max_level(n, wavelet)  # pywt.dwt_max_level(n,wavelet)
    else:
        level = int(level)
    print("    '-> \033[1;32mDecomposition level is %d\033[1;0m" % level)
    # [coefficients, frequencies] = pywt.cwt(b_sampled, np.arange(1,5), 'morl')
    # scale = pywt.frequency2scale('morl', np.array([1,10,100])/freq)
    # scale = pywt.frequency2scale('morl', np.arange(freq/100,freq)/freq)
    # scale = 2**np.arange(0,level) #2** mimcs the DWT
    scale = np.arange(1, level)  # 2** mimcs the DWT

    check_wavelet(wavelet, "continuous")
    print(pywt.scale2frequency(wavelet, scale) / (1 / freq))

    [coefficients, frequencies] = pywt.cwt(
        b_sampled, scale, wavelet, sampling_period=1 / freq
    )
    return coefficients, frequencies, scale


def plot_wave_cont(b_sampled, frequencies, freq, scale, t, coefficients):
    time_disc = t[0] + 1 / freq * np.arange(0, len(b_sampled))
    power = (
        abs(coefficients)
    ) ** 2  # probably error on https://ataspinar.com/2018/12/21/a-guide-for-using-the-wavelet-transform-in-machine-learning/
    counter = 0
    for (
        i
    ) in (
        scale
    ):  # see Continuous wavelet transform properties @ https://en.wikipedia.org/wiki/Continuous_wavelet_transform
        power[counter] = 1 / i * power[counter]
        counter = counter + 1
    fig, ax = plt.subplots(figsize=(12, 4))
    im = ax.contourf(
        time_disc,
        frequencies,
        power,
        np.arange(0, power.max(), power.max() / 10),
        extend="neither",
        cmap=plt.cm.seismic,
    )
    # fig.colorbar(im, cax=cbar_ax, orientation="vertical")
    fig.colorbar(im, ax=ax)
    ax.set_ylabel("Frequency (Hz)", fontsize=18)
    ax.set_xlabel("Time (s)", fontsize=18)
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)
    fig.tight_layout()
    plt.show()
    return fig


def wavelet_disc(b_sampled, wavelet, level):
    # Discrete Wavelet:
    check_wavelet(wavelet, "discrete")
    if isinstance(level, str) and "auto" in level:
        level = pywt.dwt_max_level(
            len(b_sampled), wavelet
        )  # pywt.dwt_max_level(n,wavelet)
    else:
        level = int(level)
    print("    '-> \033[1;32mDecomposition level is %d\033[1;0m" % level)
    coffs = pywt.wavedec(b_sampled, wavelet, level=level)
    return coffs


def plot_wave_disc(b_sampled, coffs, t, freq, level, wavelet, b):
    n = len(b_sampled)
    time_disc = t[0] + 1 / freq * np.arange(0, n)
    reconstructed_signal = pywt.waverec(coffs, wavelet, "smooth")
    f = []
    f1 = plt.figure(figsize=(12, 4))
    plt.plot(t, b, label="signal")
    plt.plot(
        time_disc,
        reconstructed_signal[0 : len(time_disc)],
        label="reconstructed levels %d" % level,
        linestyle="--",
    )
    # plt.plot(time,reconstructed_signal[0:len(time)], label='reconstructed levels %d', linestyle='--')
    plt.legend(loc="upper right")
    plt.title("single reconstruction", fontsize=20)
    plt.xlabel("time axis", fontsize=16)
    plt.ylabel("Amplitude", fontsize=16)

    # ? use recon or coffs to either create the paritallly reconstructed signal or the cofficent of the DTW:
    # ? recon -> idea is that all values are extracted just before reconstructing the signal. This adds less resolution to the upper frequencies
    # ? x ---->.g -->↓ 2 --> C1 --> ↑2 -->* g-1  #   captuere   # -->+ --> x
    # ?     '->.h -->↓ 2 --> C2 --> ↑2 -->* h-1  #      here    #  --^
    use = "recon"
    # use = 'coffs' #hold the signal, not upsample!
    cc = np.zeros((level + 1, n))
    for i in np.arange(start=level, stop=0, step=-1):
        # coffs ->  [cA_n, cD_n, cD_n-1, …, cD2, cD1]
        # reconstruction by 1) upsampling and 2) multiplying with the appropiate filter
        # page 29 on https://www.corsi.univr.it/documenti/OccorrenzaIns/matdid/matdid358630.pdf
        # GoH0+G1H1 = 1 -> Multiply a with H1 and d with G1
        # https://medium.com/@shouke.wei/process-of-discrete-wavelet-transform-iii-wavelet-partial-reconstruction-ca7a8f9420dc
        if "recon" in use:
            cc[level - i + 1] = pywt.upcoef(
                "d", coffs[level - i + 1], wavelet, level=i
            )[:n]
        else:
            # Wrong: only upsample: ‘↑ 2’ denotes ‘upsample by 2’ (put 0’s before values)
            # cc[level-i+1,::2**(i)] = coffs[level-i+1]
            # Correct: upsample is used for reconstruction, we only want to visualize -> hold the data constatnt during sample step

            counter = 0
            for j in range(0, n):
                if j % 2**i == 0:
                    cc[level - i + 1, j] = coffs[level - i + 1][counter]
                    counter = counter + 1
                else:
                    cc[level - i + 1, j] = cc[level - i + 1, j - 1]

    if "recon" in use:
        cc[0] = pywt.upcoef("a", coffs[0], wavelet, level=level)[:n]
        fig, ax = plt.subplots(nrows=level + 2, ncols=1, figsize=(12, 12))
        ax[0].plot(t, b, label="signal")
        for i in range(0, level + 1):
            if i == 0:
                sum = cc[0]
            else:
                sum = sum + cc[i]
        ax[0].plot(time_disc, sum, label="sum")
        for i in np.arange(start=level, stop=0, step=-1):
            ax[level - i + 2].plot(time_disc, cc[level - i + 1])
            ax[level - i + 2].set_title(
                f"reconstruction at level {i} from detailed coff -> [{freq / 2 ** (i + 1)}, {freq / 2**i}] Hz"
            )
        ax[1].plot(time_disc, cc[0])
        ax[1].set_title(
            f"reconstruction at level {level} from approximated coff -> [0, {freq / 2 ** (level + 1)}] Hz"
        )
        fig.legend()
        fig.tight_layout()
        f.append(fig)

    else:
        counter = 0
        for j in range(0, n):
            if j % 2**level == 0:
                cc[0, j] = coffs[0][counter]
                counter = counter + 1
            else:
                cc[0, j] = cc[0, j - 1]

    # Use freq or level to plot either the frequency or the level in the y-axis
    show = "freq"
    f_2 = plt.figure(figsize=(12, 4))
    plt.xlabel("Time (s)", fontsize=18)
    # plt.title('Discrete Wavelet Transform with %d decompositions'%level)
    if "freq" in show:
        plt.ylabel("Frequency (Hz)", fontsize=18)
        plt.xticks(fontsize=18)
        plt.yticks(fontsize=18)
        y = np.concatenate(
            [np.array([0]), freq / 2 ** np.arange(start=level + 1, stop=0, step=-1)]
        )
        x = (
            -2 / freq + t[0] + 1 / freq * np.arange(0, len(b_sampled) + 1)
        )  # ? add corner shifted by half a sample step
        X, Y = np.meshgrid(x, y)
        # plt.pcolormesh(X, Y,abs(cc),cmap=plt.cm.coolwarm,shading='flat')
        plt.pcolormesh(X, Y, abs(cc), cmap=plt.cm.seismic, shading="flat")
    else:
        y = np.arange(start=level, stop=-1, step=-1)
        x = t[0] + 1 / freq * np.arange(0, len(b_sampled))
        X, Y = np.meshgrid(x, y)
        plt.pcolormesh(X, Y, abs(cc), cmap=plt.cm.coolwarm)
        plt.ylabel("decomposition level")
        # cc = np.flip(cc,0)
        plt.gca().invert_yaxis()

    # plt.pcolormesh(X, Y, cc,cmap=plt.cm.seismic)
    # plt.pcolormesh(X, Y,abs(cc),cmap=plt.cm.seismic,shading='flat')
    # plt.plot(X.flat, Y.flat, 'x', color='m')
    plt.colorbar()
    f.append(f_2)
    plt.tight_layout()
    f.append(f1)
    return cc, f


def check_wavelet(wavelet, mode="discrete"):
    """check that the wavelet selected is supported

    Args:
        wavelet (str): wavelet name
        mode (str, optional): Wavelet mode. Defaults to "discrete".

    Raises:
        Exception: exits the program on unsupported mode
    """
    check = False
    for supported_wavelet in pywt.wavelist(kind=mode):
        if wavelet == supported_wavelet:
            check = True
            break
    if check is False:
        raise ValueError(
            "Unsupported wavelet specified, suported modes are: %s\nsee: https://pywavelets.readthedocs.io/en/latest/ref/wavelets.html "
            % pywt.wavelist(kind=mode)
        )
        # sys.exit()
    else:
        return


def welch(b, freq):
    """Welch method for spectral density estimation.

    Args:
        b (list[float]): bandwidth over time
        freq (float): sampling frequency
    """
    # f, Pxx_den = signal.welch(b, freq, 'flattop', 10000, scaling='spectrum', average='mean')
    f, Pxx_den = signal.welch(
        b, freq, "flattop", freq * 256, scaling="spectrum", average="mean"
    )
    plt.semilogy(f, np.sqrt(Pxx_den))
    plt.xlabel("frequency [Hz]")
    # plt.ylabel('PSD [V**2/Hz]')
    plt.ylabel("Linear spectrum [V RMS]")
    plt.show()