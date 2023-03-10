def parse_arg():
    import argparse
    from renderer.args import parse_args
    parser = argparse.ArgumentParser()
    parser.add_argument('--fps', type=int, default=10)
    parser.add_argument('--view_file', type=str, default='views.txt')
    return parse_args(parser)


def main():
    import imageio
    import mitsuba
    import numpy as np
    from tqdm import tqdm
    from renderer.wrapper import build_scene
    from renderer.points_loader import load_points, get_output_path
    assert args.file.exists()
    points = load_points(args.file)
    print(f"load the scene from: {args.file}")
    print(f"point cloud shape: {points.shape}")

    imgs = []
    views = np.loadtxt(args.view_file)
    scene = build_scene(points, views, args.pose, cfgs, args)
    for i in tqdm(iterable=range(views.shape[0]), desc=f"moving view"):
        img = mitsuba.render(scene, sensor=i)
        imgs.append(mitsuba.util.convert_to_bitmap(img).convert(
            mitsuba.Bitmap.PixelFormat.RGB, mitsuba.Struct.Type.UInt8, srgb_gamma=True
        ))

    file = get_output_path(args, 'gif')
    print(f"save to {file}")
    imageio.mimsave(file, imgs, fps=args.fps)


if __name__ == '__main__':
    from renderer import init_mitsuba

    cfgs, args = parse_arg()
    init_mitsuba(cfgs, args)
    main()
