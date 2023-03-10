def parse_arg():
    import argparse
    from renderer.args import parse_args
    parser = argparse.ArgumentParser()
    parser.add_argument('--fps', type=int, default=10)
    parser.add_argument('--axis', type=float, nargs=4, default=[0, 0, 360, 5],
                        help='axis begin end interval (degrees)')
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
    axis_ind = int(args.axis[0]) - 1
    axis_rot = np.arange(*args.axis[1:])
    for rot in tqdm(iterable=axis_rot, desc=f"rotating ({'xyz'[axis_ind]})"):
        from scipy.spatial.transform import Rotation
        obj_rot = Rotation.from_euler('xyz', args.pose[3:], degrees=True).as_matrix()
        addition_rot = Rotation.from_euler('xyz'[axis_ind], rot, degrees=True).as_matrix()
        rot = Rotation.from_matrix(addition_rot @ obj_rot).as_euler('xyz', degrees=True)
        pose = [*args.pose[:3], *rot]
        scene = build_scene(points, [args.view], pose, cfgs, args)
        img = mitsuba.render(scene)
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
