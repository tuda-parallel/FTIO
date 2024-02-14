# NEK5000

The trace can be downloaded from: <https://hpcioanalysis.zdv.uni-mainz.de/trace/64ed13e0f9a07cf8244e45cc>.
<!-- In case it is no longer available, the trace can be simply extracted from the provided tar archive.  -->

After downloading, rename the file to `nek_2048.darshan`. `ftio` can now be called on the complete trace via:

```sh
ftio nek_2048.darshan
```

pass the `-e no` flag to avoid generating plots and just directly obtaining the result from `ftio` on the command line:

```
ftio nek_2048.darshan -e no
```

To limit the time window to 56,000 s, pass the `-te 56000` flag as follows:

```
ftio nek_2048.darshan  -te 56000 -e no
```

<p align="right"><a href="#nek5000">⬆</a></p>