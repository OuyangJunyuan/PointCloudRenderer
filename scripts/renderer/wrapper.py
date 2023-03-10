import mitsuba
from mitsuba import ScalarTransform4f

import numpy as np


def rotate_points(points, rot):
    from scipy.spatial.transform import Rotation
    coords, feats = points[..., :3], points[..., 3:]
    rot = Rotation.from_euler('xyz', rot,degrees=True).as_matrix()
    coords = coords @ rot.T
    points = np.concatenate((coords, feats), axis=-1)
    return points


def create_environment(**kwargs) -> dict:
    scene = {}
    integer = {
        # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#integrators
        # A path refers to a chain of scattering events that starts at the light source and ends at the camera
        # It is oten useful to limit the path depth when rendering scenes for preview purposes,
        # since this reduces the amount of computation that is necessary per pixel.
        # Furthermore, such renderings usually converge faster and therefore need fewer samples per pixel.
        "type": "path",
        "max_depth": kwargs.get('max_depth', -1),  # -1 means infinite.
    }
    light_scale = kwargs.get('light_size', 10)
    area_emitter = {
        # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#emitters
        # the light source.
        # note that area light should be attached to a geometry object, as mentioned in the above link.
        "type": "rectangle",
        "to_world": ScalarTransform4f.look_at(origin=[0, 0, kwargs.get('light_z', 20)],
                                              target=[0, 0, 0],
                                              up=[1, 0, 0])
                    @ ScalarTransform4f.scale([light_scale, light_scale, 1]),
        "emitter": {
            "type": "area",
            "radiance": {
                "type": "spectrum",
                "value": kwargs.get('light_power', 6)
            }
        }
    }
    views_dict = {
        f"sensor_{i}": {  # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#sensors
            "type": "perspective",
            "near_clip": 0.1,  # Distance to the near clip planes
            "far_clip": 100.0,  # Distance to the far clip planes
            "to_world": ScalarTransform4f.look_at(origin=view[:3],
                                                  target=view[3:],
                                                  up=[0, 0, 1]),
            "film": {  # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#films
                "type": "hdrfilm",  # high dynamic render
                "width": kwargs.get("width", 1920),  # width of the camera snesor in pixel
                "height": kwargs.get("height", 1080),  # height of the camera snesor in pixel
                "rfilter": {"type": "gaussian"}  # reconstruction filter
            },
            "sampler": {  # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#samplers
                "type": "independent",  # independent sampling with a uniform distribution.
                "sample_count": kwargs.get("sample", 1)  # the higher, the better, which result have less noise.
            }
        } for i, view in enumerate(kwargs.get('views', [[0, 2.5, 1.5, 0, 0, 0]]))
    }

    material = {
        # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#bsdfs
        "roughplastic": {
            # https://mitsuba2.readthedocs.io/en/latest/generated/plugins.html#rough-plastic-material-roughplastic
            "type": "roughplastic",
            "distribution": "ggx",
            "alpha": 0.05,
            "int_ior": 1.46,
            "diffuse_reflectance": {
                "type": "rgb",
                "value": [1, 1, 1]
            }
        }
    }
    scene = {
        "type": "scene",
        "integer": integer,
        "emitter": area_emitter,
        **views_dict,
        **material
    }
    return scene


def create_ground() -> dict:
    ground = {  # to make shadow
        "type": "rectangle",
        "bsdf": {
            "type": "ref",
            "id": "roughplastic"
        },
        "to_world": ScalarTransform4f.translate([0, 0, -0.5])
                    @ ScalarTransform4f.scale([10, 10, 1]),
    }
    return ground


def create_cloud(points: np.ndarray, **kwargs) -> dict:
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

    """
    points: points should be organized as [num_pts, coords(x,y,z)].
    """
    xyz = points[..., :3]
    if 'rgb' in kwargs['format']:
        ind = kwargs['format'].find('rgb')
        colors = points[ind:ind + 3]
    else:
        import matplotlib.pyplot as plt
        if kwargs['color_by'] and kwargs['color_by'] in kwargs['format']:
            ind = kwargs['format'].find(kwargs['color_by'])
            vec = points[..., ind:ind + len(kwargs['color_by'])]
        else:
            mins = np.amin(xyz, axis=0)
            maxs = np.amax(xyz, axis=0)
            scale = np.amax(maxs - mins)
            vec = ((xyz - mins) / scale).astype(np.float32)
        norm = np.linalg.norm(vec, axis=-1, keepdims=True)
        if kwargs['color_normalize']:
            norm /= np.amax(norm)
        color_map = plt.get_cmap(kwargs['color_map'])
        colors = color_map(norm)[:, 0, :3]

    if kwargs['point_size']:
        sizes = np.ones((xyz.shape[0], 1)) * kwargs['point_size']
    elif 's' in kwargs['format']:
        ind = kwargs['format'].find('s')
        sizes = points[..., ind:ind + 1]
    else:
        sizes = np.ones((xyz.shape[0], 1)) * kwargs['default_point_size']

    collector = {"type": "shapegroup"}
    for idx in range(xyz.shape[0]):
        collector[str(int(idx))] = create_ball(coord=xyz[idx], color=colors[idx], size=sizes[idx])

    points_dict = {
        "type": "instance",
        "points": collector,
    }
    return points_dict


def build_scene(points, views, pose, cfgs, args):
    from mitsuba import load_dict

    xyz, features = points[..., :3], points[..., 3:]
    xyz *= args.scale
    xyz = rotate_points(xyz, pose[3:])
    xyz = xyz + np.array(pose[:3])

    scene_dict = create_environment(views=views, **cfgs, **args)
    scene_dict.update(pointcloud_1=create_cloud(np.concatenate((xyz, features), axis=-1), **cfgs, **args))
    scene_dict['ground_plane'] = create_ground()
    return load_dict(scene_dict)


# def render(scene, view_ind=0):
#     from mitsuba import Bitmap, Struct, render
#     # sensor = scene.sensors()[view_ind]  # select the first camera to have a view.
#     # scene.integrator().render(scene, sensor)
#     img = render(scene, spp=128)
#     # film = sensor.film()
#     # img = film.bitmap(raw=True).convert(Bitmap.PixelFormat.RGB, Struct.Type.UInt8, srgb_gamma=True)
#     return img
