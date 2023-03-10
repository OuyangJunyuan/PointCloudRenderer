def parse_arg():
    import argparse
    from renderer.args import parse_args
    parser = argparse.ArgumentParser()
    return parse_args(parser)


def main():
    import mitsuba
    from renderer.points_loader import get_output_path
    if args.xml is not None:
        from mitsuba import load_file
        print(f"load the scene from: {args.xml}")
        assert args.xml.exists()
        scene = load_file(args.xml.__str__())
    else:
        from renderer.points_loader import load_points
        from renderer.wrapper import build_scene
        print(f"load the scene from: {args.file}")
        assert args.file.exists()
        points = load_points(args.file)

        print(f"point cloud shape: {points.shape}")
        scene = build_scene(points, [args.view], args.pose, cfgs, args)

    img = mitsuba.render(scene)

    file = get_output_path(args, 'jpg')
    print(f"save to {file}")
    mitsuba.util.write_bitmap(file, img)


if __name__ == '__main__':
    from renderer import init_mitsuba

    cfgs, args = parse_arg()
    init_mitsuba(cfgs, args)
    main()
