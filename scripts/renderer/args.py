def parse_args(parser):
    import yaml
    import argparse
    from pathlib import Path
    from easydict import EasyDict
    ####################################################################################################################
    input_parser = parser.add_mutually_exclusive_group()
    input_parser.add_argument('-f', '--file', type=Path, help='input point cloud file')
    input_parser.add_argument('-x', '--xml', type=Path, help='scene .xml file')
    parser.add_argument('-o', '--output', type=Path, default=Path('./'), help='output dir or file')
    parser.add_argument('--format', type=str, default='xyz')
    ####################################################################################################################
    parser.add_argument('--point_size', type=float, default=None)
    parser.add_argument('--default_point_size', type=float, default=0.02)
    parser.add_argument('--scale', type=float, default=1, help='point cloud scale')
    ####################################################################################################################
    parser.add_argument('--color_by', type=str, default=None)
    parser.add_argument('--color_map', type=str, default='turbo')
    parser.add_argument('--color_normalize', action='store_true', default=False)
    ####################################################################################################################
    parser.add_argument('--pose', type=float, nargs=6, default=[0, 0, 0, 0, 0, 0], help='object pose,XYZ-RPY(deg)')
    parser.add_argument('--view', type=float, nargs=6, default=[0, 2.5, 1.5, 0, 0, 0], help='origin->target')
    ####################################################################################################################
    parser.add_argument('--config', type=Path, default=Path('config.yaml'))
    parser.add_argument('--preview', action='store_true', default=False, help='fast rendering to preview')
    ####################################################################################################################
    args = EasyDict(vars(parser.parse_args()))
    cfgs = EasyDict(yaml.safe_load(open(args.config)))
    if args.preview:
        cfgs.sample = 1
        cfgs.max_depth = 2
    return cfgs, args
