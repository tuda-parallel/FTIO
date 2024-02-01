from __future__ import annotations
import argparse


def parse_args(argv:list) -> argparse.Namespace:
    name = argv[0]
    # name = name[name.rfind('/')+1:-3]
    name = name[name.rfind('/')+1:]

    if 'ioplot' in name:
        disc = 'Plots result stored in Json file to a HTML page or PDF document.'
    elif 'ftio' in name or 'predictor' in name:
        disc = 'Performs discrete fourier transformation (DFT) on a JSON file. The JSON files can be created with executing a code with tmio preloaded. There are severa parameters which can be controlled for the DFT.'
    elif 'parse' in name:
        disc = 'Parses to an extra-p format.'
    else:
        disc = ''

    parser = argparse.ArgumentParser(
        prog=name,#.capitalize(),
        description=disc,
        epilog="""
--------------------------------------------
Author: 
Ahmad H. Tarraf.

REPORTING BUGS
Report any translation bugs to <some_git_website>

COPYRIGHT
Copyright  ©  

SEE ALSO
Full documentation <paper_link>
--------------------------------------------
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
        )
    
    parser.add_argument('files', metavar='files', type = str, nargs='+', help='file, file list (file 0 ... file n), folder, or foder list (folder 0.. folder n) to plot')    
    parser.add_argument('-m', '--mode', dest = 'mode',      type = str ,  help ='mode: eiher async_write, async_read, sync_write, sync_read')
    
    
    if 'parse' not in name.lower():
        parser.add_argument('-r', '--render', dest='render',  type = str ,  help ='render: eiher dynamic (default) or static. static only prints a single file' )
        parser.set_defaults(render="dynamic")

    if 'play' in name.lower():
        parser.add_argument('-f', '--freq', dest='freq', type = float, help ='Specifies the sampling rate of the discretization of the signal. This directly affects the lowest highest captured frequency (Nyquist). FREQ is specified in Hz, In case this value is set to -1, the auto mode is launched which specifies FREQ as the smallest change in the bandwidth is detected, and the FREQ is set to this  value. Note that the lowest allowed frequency in the auto mode is 2000 Hz')
        parser.add_argument('-e', '--engine',         type = str, help = 'Plot engine. Either plotly (default) or mathplotlib. Specifies the engine used to display the figures. Plotly is used to generate HTML files')
        parser.set_defaults(engine = 'plotly')

    if 'ftio' in name.lower() or 'predictor' in name.lower():
        parser.set_defaults(mode="sync write")
        parser.add_argument('-f', '--freq', dest='freq', type = float, help ='Specifies the sampling rate of the discretization of the signal. This directly affects the lowest highest captured frequency (Nyquist). sampling_rate is specified in Hz, In case this value is set to -1, the auto mode is launched which specifies the sampling-.rate as the smallest change in the bandwidth is detected, and the sampling_rate is set to this  value. Note that the lowest allowed frequency in the auto mode is 2000 Hz')
        parser.set_defaults(freq = 10)
        parser.add_argument('-ts', '--ts',         type = float, help = 'start time')
        parser.add_argument('-te', '--te',         type = float, help = 'end time')
        parser.add_argument('-tr', '--transformation', dest='transformation',  type = str, help = 'freq_technique: frequency technique to use. Supported modes are: dft (default), wave_disc, and wave_cont.')
        parser.set_defaults(transformation='dft')
        parser.add_argument('-e', '--engine',         type = str, help = 'Plot engine. Ether plotly (default) or mathplotlib. Specifies the engine used to display the figures. Plotly is used to generate HTML files.')
        parser.set_defaults(engine = 'plotly')
        parser.add_argument('-o', '--outlier',         type = str, help = 'Outlier detection method: Z-score, DB-Scan, Isolation_forest, or LOF')
        parser.set_defaults(outlier = 'Z-score')
        parser.add_argument('-le', '--level', dest='level', type = float, help ='Specifies the decomposition level for the discret wavelet transformation (default=3). If specified as ""auto"", the maximum decomposition level is automatic calulcated')
        parser.set_defaults(level = 3)
        parser.add_argument('-t', '--tol', dest= 'tol',   type = float, help ='')
        parser.set_defaults(tol =  0.8)
        parser.add_argument('-d', '--dtw', action='store_true', help ='Performs dynamic time wrapping on the top 3 frequencies (highest amplitude) calculated using the DFT if true')
        parser.add_argument('-nd', '--no-dtw', dest='dtw', action='store_false', help='Disables DTW calculation (default)')
        parser.set_defaults(dtw=False)
        parser.add_argument('-re', '--reconstruction', action='store_true', help ='Plots reconstruction of top 10 sgnals on figure')
        parser.add_argument('--no-reconstruction', dest='reconstruction', action='store_false', help='Disables reconstruction of top 10 signals (default)')
        parser.set_defaults(reconstruction=False)
        parser.add_argument('-p', '--psd', action='store_true', help ='psd: if set, replace the amplitude spectrum (a) clclualtion with power density spectrum (a*a/N)')
        parser.set_defaults(psd=True)
        parser.add_argument('-np','--no-psd', dest='psd', action='store_false', help='')
        parser.add_argument('-c', '--autocorrelation', dest='autocorrelation', action='store_true', help ='autocorrelation: if set, autocorreleation is calculated in addition to dft. At the end, the results are merged to a single prediction.')
        parser.set_defaults(autocorrelation=False)
        parser.add_argument('-w', '--window_adaptation', dest='window_adaptation', action='store_true', help ='time window adaptation: if set to true, the time window is shifted on X hits to X times the previous phases from the current instance. X corresponds to "frequency_hits". ')
        parser.set_defaults(window_adaptation=False)
        parser.add_argument('-fh', '--frequency_hits', dest= 'frequency_hits',   type = float, help ='frequency hits: specifies the nuumber of hits needed to adapt the time window. An hit occurs once an dominant freuqency is found.')
        parser.set_defaults(frequency_hits =  3)
        parser.add_argument('-v', '--verbose', dest= 'verbose',   action = 'store_true', help ='sets verbose on or off (default=False)')
        parser.set_defaults(verbose =  False)

    if 'ioplot' in name.lower():
        parser.set_defaults(mode="")
        parser.add_argument('-z', '--zoom',       type = float, help ='Zoom: upper zoom limit on the y-axis')
        parser.add_argument('-t', '--threaded', action='store_true', help= 'Turn multithreading on')
        parser.add_argument('-nt', '--no-threaded', dest='threaded', action='store_false')
        parser.set_defaults(threaded=True)
        parser.add_argument('-e', '--engine',         type = str, help = 'Plot engine: Either plotly (default) or dash')
        parser.set_defaults(engine = 'plotly')
        parser.add_argument('--n_shown_samples', type=int, help='Only for dash: Number of shown samples per trace (default: 20_000). Caution: Too small numbers could lead to incorrect representations!')
        parser.set_defaults(n_shown_samples=20_000)
        parser.add_argument('--merge_plots', action='store_true', help='Only for dash: Merges the plots to one plot for each io mode. Note: The file dropdwon menu then has no functionality.')
        parser.set_defaults(merge_plots=False)

    # Data modes
    parser.add_argument('-s', '--sum', action='store_true', help ='sum plot: True or False')
    parser.add_argument('-ns', '--no-sum', dest='sum', action='store_false')
    parser.set_defaults(sum=True)
    parser.add_argument('-a', '--avr', action='store_true', help ='avr plot: True or False')
    parser.add_argument('-na', '--no-avr', dest='avr', action='store_false')
    parser.set_defaults(avr=True)
    parser.add_argument('-i', '--ind', action='store_true', help ='ind plot: True or False')
    parser.add_argument('-ni', '--no-ind', dest='ind', action='store_false')
    parser.set_defaults(ind=False)

    parser.add_argument('-x', '--dxt_mode', dest='dxt_mode',  type = str ,  help ='Select data to extract from darshan traces (DXT_POSIX or DXT_MPIIO (default))')
    parser.set_defaults(dxt_mode='DXT_MPIIO')
    parser.add_argument('-l', '--limit',      type = int,   help ='Max ranks: limit the number of ranks')
    parser.set_defaults(limit=-1)


    args = parser.parse_args(argv)
    #default values:


    return args