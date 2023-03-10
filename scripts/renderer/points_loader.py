import numpy as np


def load_points(filename):
    if filename.suffix == '.npy':
        return np.load(filename)
    else:
        raise NotImplementedError('implement your own points loader')


def get_output_path(args, suffix='jpg'):
    from pathlib import Path
    if args.output.is_dir():
        args.output.mkdir(exist_ok=True, parents=True)
        args.output /= Path(args.file).stem
    output = args.output
    output = output.with_suffix('.' + suffix)
    if output.exists():
        import os
        output = output.with_name(output.stem + '_' + str(int(100 * os.times().elapsed)) + output.suffix)
    return output.__str__()
