from __future__ import annotations
import argparse
from ftio import __copyright__, __repo__, __version__, __liscence__



def parse_args(argv:list) -> argparse.Namespace:
    name = argv[0]
    # name = name[name.rfind('/')+1:-3]
    name = name[name.rfind('/')+1:]

    if 'plot' in name:
        disc = 'Plots result stored in Json file to a HTML page or PDF document.'
    elif 'ftio' in name:
        disc = 'Captures the period of the I/O phases. Uses freqeuncy techniques (default=discrete fourier transformation) and outlier detection methods (Z-score) on the provided file. Supported file formats are Json, Jsonlines, Msgpack, Darshan, and REcorder (folder). TMIO can be used to generate the tracing file needed. There are several parameters which can be controlled by the arguments bellow.'
    elif 'predictor' in name:
        disc = 'Wrapper code to execute ftio online. Monitors a file for changes. Whenever the file is modified (i.e., new traces are appended) a new prediction process is executed and the result is store in a shared memory space. All parameters that can be passed to ftio are supported by predictor.'
    elif 'parse' in name:
        disc = 'Parses to an extra-p format.'
    else:
        disc = ''

    parser = argparse.ArgumentParser(
        prog=name,#.capitalize(),
        description=disc,
        epilog=f'''
--------------------------------------------
Author: 
Ahmad H. Tarraf

Report any bugs to:
{__repo__}/issues

COPYRIGHT:
{__copyright__} 

LISCENCE:
{__liscence__} 

Full documentation:
{__repo__}
--------------------------------------------
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
        )
    
    parser.add_argument('files', metavar='files', type = str, nargs='+', help='file, file list (file 0 ... file n), folder, or folder list (folder 0.. folder n)')    
    parser.add_argument('-m', '--mode', dest = 'mode',      type = str ,  help ='if the trace file contains several I/O modes, a specific mode can be selected. Supported modes are: async_write, async_read, sync_write, sync_read')
    
    
    if 'parse' not in name.lower():
        parser.add_argument('-r', '--render', dest='render',  type = str ,  help ='specifies how the plots are rendered. Either dynamic (default) or static' )
        parser.set_defaults(render='dynamic')

    if 'play' in name.lower():
        parser.add_argument('-f', '--freq', dest='freq', type = float, help ='specifies the sampling rate with which the continuous signal is discretized (default=10Hz). This directly affects the highest captured frequency (Nyquist). The value is specified in Hz. In case this value is set to -1, the auto mode is launched which sets the sampling frequency automatically to the smallest change in the bandwidth detected. Note that the lowest allowed frequency in the auto mode is 2000 Hz')
        parser.add_argument('-e', '--engine',         type = str, help = 'plot engine. Either plotly (default) or mathplotlib. Specifies the engine used to display the figures. Plotly is used to generate HTML files')
        parser.set_defaults(engine = 'plotly')

    if 'ftio' in name.lower() or 'predictor' in name.lower():
        parser.set_defaults(mode='sync write')
        parser.add_argument('-f', '--freq', dest='freq', type = float, help ='specifies the sampling rate with which the continuous signal is discretized (default=10Hz). This directly affects the highest captured frequency (Nyquist). The value is specified in Hz. In case this value is set to -1, the auto mode is launched which sets the sampling frequency automatically to the smallest change in the bandwidth detected. Note that the lowest allowed frequency in the auto mode is 2000 Hz')
        parser.set_defaults(freq = 10)
        parser.add_argument('-ts', '--ts',         type = float, help = 'modifies the start time of the examined time window')
        parser.add_argument('-te', '--te',         type = float, help = 'modifies the end time of the examined time window')
        parser.add_argument('-tr', '--transformation', dest='transformation',  type = str, help = 'Specifies the frequency technique to use. Supported modes are: dft (default), wave_disc, and wave_cont')
        parser.set_defaults(transformation='dft')
        parser.add_argument('-e', '--engine',         type = str, help = 'specifies the engine used to display the figures. Either plotly (default) or mathplotlib can be used.  Plotly is used to generate interactive plots as HTML files. Set this value to no if you do not want to generate plots')
        parser.set_defaults(engine = 'plotly')
        parser.add_argument('-o', '--outlier',         type = str, help = 'outlier detection method: Z-score (default), DB-Scan, Isolation_forest, or LOF')
        parser.set_defaults(outlier = 'Z-score')
        parser.add_argument('-le', '--level', dest='level', type = float, help ='specifies the decomposition level for the discrete wavelet transformation (default=3). If specified as auto, the maximum decomposition level is automatic calculated')
        parser.set_defaults(level = 3)
        parser.add_argument('-t', '--tol', dest= 'tol',   type = float, help ='tolerance value')
        parser.set_defaults(tol =  0.8)
        parser.add_argument('-d', '--dtw', action='store_true', help ='performs dynamic time wrapping on the top 3 frequencies (highest contribution) calculated using the DFT if set (default=False)')
        parser.set_defaults(dtw=False)
        parser.add_argument('-re', '--reconstruction', action='store_true', help ='plots reconstruction of top 10 signals on figure')
        parser.set_defaults(reconstruction=False)
        parser.add_argument('-np','--no-psd', dest='psd', action='store_false', help='if set, replace the power density spectrum (a*a/N) with the amplitude spectrum (a)')
        parser.set_defaults(psd=True)
        parser.add_argument('-c', '--autocorrelation', dest='autocorrelation', action='store_true', help ='if set, autocorrelation is calculated in addition to DFT. The results are merged to a single prediction at the end')
        parser.set_defaults(autocorrelation=False)
        parser.add_argument('-w', '--window_adaptation', dest='window_adaptation', action='store_true', help ='online time window adaptation. If set to true, the time window is shifted on X hits to X times the previous phases from the current instance. X corresponds to frequency_hits')
        parser.set_defaults(window_adaptation=False)
        parser.add_argument('-fh', '--frequency_hits', dest= 'frequency_hits',   type = float, help ='specifies the number of hits needed to adapt the time window. A hit occurs once a dominant frequency is found')
        parser.set_defaults(frequency_hits =  3)
        parser.add_argument('-v', '--verbose', dest= 'verbose',   action = 'store_true', help ='sets verbose on or off (default=False)')
        parser.set_defaults(verbose =  False)

    if 'plot' in name.lower():
        parser.set_defaults(mode='')
        parser.add_argument('-z', '--zoom',       type = float, help ='upper zoom limit on the y-axis')
        parser.add_argument('-nt', '--no-threaded', dest='threaded', action='store_false', help= 'turn multithreading off (default=on)')
        parser.set_defaults(threaded=True)
        parser.add_argument('-e', '--engine',         type = str, help = 'plot engine to use. Either plotly (default), dash, or matplotlib')
        parser.set_defaults(engine = 'plotly')
        parser.add_argument('--n_shown_samples', type=int, help='only for dash: Number of shown samples per trace (default: 20_000). Caution: Too small numbers could lead to incorrect representations!')
        parser.set_defaults(n_shown_samples=20_000)
        parser.add_argument('--merge_plots', action='store_true', help='only for dash: Merges the plots to one plot for each io mode. Note: The file dropdown menu then has no functionality')
        parser.set_defaults(merge_plots=False)
        parser.add_argument('--no_disp', action='store_true', help='avoids opening the generated HTML file')
        parser.set_defaults(no_disp=False)
    if 'parse' in name.lower():
        parser.add_argument('--scale',  action='store_true', help ='scales the Y-axis')
        parser.set_defaults(scale=False)    
    # Data modes
    parser.add_argument('-s', '--sum', action='store_true', help ='sum plot: True (default) or False')
    parser.add_argument('-ns', '--no_sum', dest='sum', action='store_false')
    parser.set_defaults(sum=True)
    parser.add_argument('-a', '--avr', action='store_true', help ='avr plot: True (default) or False')
    parser.add_argument('-na', '--no_avr', dest='avr', action='store_false')
    parser.set_defaults(avr=True)
    parser.add_argument('-i', '--ind', action='store_true', help ='ind plot: True or False (default)')
    parser.add_argument('-ni', '--no_ind', dest='ind', action='store_false')
    parser.set_defaults(ind=False)
    parser.add_argument('-cf', '--custom_file',   type = str, help = 'passes a [path/filename.py] file containing the translation and pattern for a custom file format similiar to:\n https://github.com/tuda-parallel/FTIO/blob/main/examples/txt/custom_input.py')
    parser.set_defaults(custom_file = '')
    
    parser.add_argument('-x', '--dxt_mode', dest='dxt_mode',  type = str ,  help ='select data to extract from Darshan traces (DXT_POSIX or DXT_MPIIO (default))')
    parser.set_defaults(dxt_mode='DXT_MPIIO')
    parser.add_argument('-l', '--limit',      type = int,   help ='max ranks to consider when reading a folder')
    parser.set_defaults(limit=-1)


    args = parser.parse_args(argv)
    #default values:


    return args
