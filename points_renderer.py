import os

import matplotlib.pyplot as plt
import mitsuba
import argparse
import numpy as np
from pathlib import Path
from matplotlib import pyplot


def parse_arg():
    parser = argparse.ArgumentParser(description='a point render develop with mitsuba python API')
    parser.add_argument('-v', '--variant', type=str, default='scalar_spectral', help='specify the variant of mitsuba')
    parser.add_argument('-f', '--file', type=str, required=True, help='specify the rendered point cloud')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='specify where the render result image should be stored')
    parser.add_argument('-s', '--sample', type=int, default=1, help='specify the sample times, default 1 for preview')
    parser.add_argument('-x', '--xml', type=str, default=None, help='specify the scene description file')
    parser.add_argument('-c', '--color', type=str, default="default", help='specify the type for color mapping')
    return parser.parse_args()


args = parse_arg()
assert args.variant in mitsuba.variants(), f'the given variant is no supported, please recompile mitsuba.'
mitsuba.set_variant(args.variant)
from mitsuba.core import Thread, Bitmap, Struct, ScalarTransform4f
from mitsuba.core.xml import load_file, load_dict


def get_output_path(p):
    output_file = Path('output.jpg' if p is None else p)
    if output_file.suffix != '.jpg':
        output_file = output_file.with_suffix(".jpg")
    if output_file.exists():
        temp = output_file.with_name(
            output_file.stem + '_' + str(int(100 * os.times().elapsed)) + output_file.suffix)
        output_file = temp
    return output_file.__str__()


def create_environment(**kwargs) -> dict:
    print(f"create environment ...")
    integer = {  # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#integrators
        "type": "path",
        "max_depth": -1,  # Specifies the longest path depth in the generated output image, -1 means infinit.
        # "samples_per_pass": 4,
    }
    area_emitter = {  # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#emitters
        # note that area light should be attached to a geometry object, as mentioned in the above link.
        "type": "rectangle",
        "to_world": ScalarTransform4f.look_at(origin=[-4, -4, 20],
                                              target=[0, 0, 0],
                                              up=[0, 0, 1])
                    * ScalarTransform4f.scale([10, 10, 1]),
        "emitter": {
            "type": "area",
            "radiance": {
                "type": "rgb",
                "value": [6, 6, 6]
            }
        }
    }
    film = {  # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#films
        "type": "hdrfilm",  # high dynamic render
        "width": 1920,  # width of the camera snesor in pixel
        "height": 1080,  # height of the camera snesor in pixel
        "rfilter": {"type": "gaussian"}  # reconstruction filter
    }
    sampler = {  # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#samplers
        "type": "independent",  # independent sampling with a uniform distribution.
        "sample_count": kwargs["sample"]  # the higher the better, which result have less noise.
    }
    camera = {  # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#sensors
        "type": "perspective",
        "near_clip": 0.1,  # Distance to the near clip planes
        "far_clip": 100.0,  # Distance to the far clip planes
        "to_world": ScalarTransform4f.look_at(origin=[3, 3, 3],
                                              target=[0, 0, 0],
                                              up=[0, 0, 1]),
        "film": film,
        "sampler": sampler
    }

    scene = {
        "type": "scene",
        "integer": integer,
        "sensor": camera,
        "emitter": area_emitter
    }
    # print(load_dict(scene))
    return scene


def create_material() -> dict:
    print(f"create material ...")
    # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#bsdfs
    roughplastic = {
        "type": "roughplastic",
        "distribution": "ggx",
        "alpha": 0.05,
        "int_ior": 1.46,
        "diffuse_reflectance": {
            "type": "rgb",
            "value": [1, 1, 1]
        }
    }

    material = {
        "roughplastic": roughplastic
    }
    return material


def create_objects(objects: list, cm):
    print(f"create objects ...")

    def colormap(coords: np.ndarray, color='default') -> np.ndarray:

        vec = np.clip(coords, 0.001, 1.0)
        norm = np.linalg.norm(vec, axis=-1, keepdims=True)
        vec /= norm
        if color is 'default':
            return vec
        else:
            color_map = plt.get_cmap(color)
            return color_map(1 - norm)[:, 0, :3]  # rgba -> rgb

    def create_ground() -> dict:
        ground = {  # to make shadow
            "type": "rectangle",
            "bsdf": {
                "type": "ref",
                "id": "roughplastic"
            },
            "to_world": ScalarTransform4f.translate([0, 0, -0.5])
                        * ScalarTransform4f.scale([10, 10, 1]),
        }
        return ground

    def create_ball(coord: np.ndarray, color: np.ndarray, size: np.ndarray) -> dict:
        ball = {
            "type": "sphere",
            "radius": size.item(),
            "to_world": ScalarTransform4f.translate(coord),
            "bsdf": {
                "type": "diffuse",
                "reflectance": {"type": "rgb", "value": color},
            }
        }
        return ball

    def create_cloud(points: np.ndarray, default_size: float = 0.025) -> dict:
        """
        points: points should be organized as [num_pts, coords(x,y,z)].
        """
        coords, colors, sizes = points[:, :3], points[:, 3:6], points[:, 6:7]
        if colors.shape[1] == 0:
            colors = colormap(coords + np.array([0.5, 0.5, + 0.5 - 0.0125]).reshape((1, 3)), color=cm)
        if sizes.shape[1] == 0:
            sizes = np.ones((coords.shape[0], 1)) * default_size

        collector = {"type": "shapegroup"}
        for idx in range(points.shape[0]):
            collector[str(int(idx))] = create_ball(coord=points[idx], color=colors[idx], size=sizes[idx])

        points_dict = {
            "type": "instance",
            "points": collector,
        }
        return points_dict

    # ground plane that shadow projected to.
    objs = {"ground_plane": create_ground(), }

    # add rest to scene dict
    num_obj = objects.__len__()
    offset = -(num_obj - 1) / 2
    for i, obj in enumerate(objects):
        if isinstance(obj, np.ndarray):
            ins_name = f'instance_{int(i)}'
            pts = np.ascontiguousarray(obj)
            objs[ins_name] = create_cloud(pts)
            objs[ins_name]['to_world'] = ScalarTransform4f.translate(
                [offset + i, -(offset + i), 0])
        else:
            raise NotImplementedError

        print(f"=> handle object {i + 1}/{objects.__len__()} ...")

    return objs


def preprocess_pointcloud(points):
    def downsample_pointcloud(pts, num_points, methods="random"):
        # TODO: maybe FPS and Others methods will be implemented here.
        if methods == "random":
            pt_indices = np.random.choice(pts.shape[0], num_points, replace=False)
            return pt_indices
        elif methods == "fps":
            raise NotImplementedError
        else:
            raise NotImplementedError

    def normalize_pointcloud(pts):
        mins = np.amin(pts, axis=0)
        maxs = np.amax(pts, axis=0)
        center = (mins + maxs) / 2.
        scale = np.amax(maxs - mins)
        normalized = ((pts - center) / scale).astype(np.float32)  # [-0.5, 0.5]
        return normalized

    coords = points[:, :3]

    sampled_indices = downsample_pointcloud(coords, 2048)
    np.random.shuffle(sampled_indices)
    sampled = coords[sampled_indices]

    result = normalize_pointcloud(sampled)
    return result


if __name__ == '__main__':
    if args.xml is not None:
        xml_path = Path(args.xml)
        assert xml_path.exists()
        print(f"xml will be read from given file\n=> {args.xml}")
        scene = load_file(xml_path.__str__())
    else:
        print(f"the variant currently used is\n=> {mitsuba.variant()}")
        filepath = Path(args.file)
        assert filepath.exists(), f'file [{filepath}] dose not exist.'

        print(f"points will be read from given file\n=> {args.file}")
        pc = np.load(filepath.__str__())
        print(f"=> shape {pc.shape}")

        # preprocess
        pc = preprocess_pointcloud(pc)
        pc = pc[:, [2, 0, 1]]
        pc[:, 0] *= -1
        pc[:, 2] += 0.0125
        object_list = [pc, pc, pc]

        # create dict for mitsuba scene description.
        scene_dict = create_environment(sample=args.sample)
        scene_dict.update(create_material())
        scene_dict.update(create_objects(object_list, args.color))

        # load scene from dict
        scene = load_dict(scene_dict)

    # start rendering
    sensor = scene.sensors()[0]  # select the first camera to have a view.
    scene.integrator().render(scene, sensor)

    # save the render result.
    film = sensor.film()
    img = film.bitmap(raw=True).convert(Bitmap.PixelFormat.RGB, Struct.Type.UInt8, srgb_gamma=True)
    save_path = get_output_path(args.output)
    img.write(save_path)
    print(f"result was stored in file\n=> {save_path}")
