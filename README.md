# gerberpeek
gerberpeek is a renderer for RS-274X Gerber data used in printed circuit boards
(PCBs). It uses pure Python and can be used to render Gerber data into PNGs.

## Usage
First, a quick look at the help page:

```
usage: gerberpeek [-h] [-d dpi] [-s filename] [-o name:filename]
                  [--debug-intermediate] [-r] [-v]
                  filename [filename ...]

Render and analyze RS-274X Gerber files.

positional arguments:
  filename              Raw Gerber files that should be processed by
                        gerberpeek. Can also supply ZIP files that will be
                        searched internally or directories (if recursive
                        operation is requested).

optional arguments:
  -h, --help            show this help message and exit
  -d dpi, --resolution dpi
                        Specifies the render resolution in dots per inch.
                        Defaults to 300 dpi.
  -s filename, --script filename
                        Specifies the render script or scripts, JSON files, to
                        run. When multiple scripts are named, they can
                        override specific settings of previous scripts, like
                        definitions or add/change render steps. Defaults to
                        only rendering 'renderscript.json'.
  -o name:filename, --outfile name:filename
                        When deliverables should be created, names the
                        deliverables and the filenames they should be stored
                        in, separated by colon. Can be specified multiple
                        times to create multiple deliverables.
  --debug-intermediate  For debugging purposes, write all intermediate
                        renderings (such as individual layers) to own files.
  -r, --recursive       When giving directories as infiles, traverse them
                        recursively, looking for files.
  -v, --verbose         Increases verbosity. Can be specified multiple times
                        to increase.
```

The default rendering script is "renderscript.json", which is already included.
If you just want to render a Gerber PCB Zipfile with its top and bottom side,
you can simply:

```
$ ./gerberpeek -o top:top.png -o bottom:bottom.png my_gerber_package.zip
```

When the files are all in one directory individually, you can also:

```
$ ./gerberpeek -o top:top.png -o bottom:bottom.png my_gerber/*
```

Or, if they're distributed in multiple directories:

```
$ ./gerberpeek -o top:top.png -o bottom:bottom.png --recursive my_gerber
```

Let's say you want to change some parameters, but keep the general Gerber
rendering in tact. For example, render the PCB in a blue color scheme for blue
FR-4/soldermask. Then you'd do:

```
$ ./gerberpeek -s renderscript.json -s colorscheme_blue.json -o top:top.png -o bottom:bottom.png my_gerber_package.zip
```

Note that the order of the "--script" parameter is important, the later options
override earlier specified ones.

## License
GNU-GPL 3.
