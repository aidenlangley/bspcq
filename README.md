# bspcq, q for query

## A `bspc` analyzer (utility for [bspwm](https://github.com/baskerville/bspwm))

This is a small program that prints a user friendly, visual representation, of
your current `bsp` tree.

The aim is to assist in using `bspwm` so new users have an easier time getting
into tiling window managers, and have some toys to play with.

It's essentially the same as
running:
```sh
bspc query -M -m <monitor-name> | jq
```

Except there are fewer parameters, and a less complex syntax, to remember.

Usage:
```sh
bspcq
bspcq -s # a simpler view, perfect for finding window class names
bspcq -m/d/n <selector> # the same as `bspc query -m/d/n <selector>`
```

### Installation

 - Will have to manually download the script at the moment.
 - Move to `~/.local/bin` or `~/bin` or `/usr/bin`, just make sure it's on
 `$PATH`.
 - `python -m pip install rich`.
 - Good to go.

### Preview


![2022-01-25_02-17_1](https://user-images.githubusercontent.com/684721/150789813-da7d0b56-1762-4bf7-af6b-7d031f779030.png)

![2022-01-25_02-17](https://user-images.githubusercontent.com/684721/150789957-06765616-661b-4486-b69a-a7b570e204e1.png)

