#!/usr/bin/env python3
"""Parametric viola da gamba fingerboard planing jig.

The jig is a rectangular printable block with a tapered cylindrical cradle
removed from its top.  X runs along the fingerboard, Y across it, and Z is up.
All dimensions are millimetres.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from build123d import (
    Align,
    Box,
    Cylinder,
    Part,
    Plane,
    Pos,
    Rectangle,
    Rot,
    export_step,
    export_stl,
    loft,
)


@dataclass(frozen=True)
class JigParameters:
    """Dimensions controlling the cradle and the surrounding block."""

    radius: float = 55.0
    fingerboard_length: float = 256.0
    jig_length: float = 250.0
    nut_width: float = 42.0
    bridge_width: float = 62.0

    # Clearance is applied on every side of the fingerboard outline.
    clearance: float = 0.25
    side_wall: float = 8.0
    base_thickness: float = 30.0
    foam_thickness: float = 5.0

    # Used only for the translucent fingerboard reference in the viewer.  The
    # unknown planed face is represented as a longitudinally sloping plane.
    fingerboard_edge_thickness: float = 6.0

    def validate(self) -> None:
        positive = {
            "radius": self.radius,
            "fingerboard_length": self.fingerboard_length,
            "jig_length": self.jig_length,
            "nut_width": self.nut_width,
            "bridge_width": self.bridge_width,
            "side_wall": self.side_wall,
            "base_thickness": self.base_thickness,
            "foam_thickness": self.foam_thickness,
            "fingerboard_edge_thickness": self.fingerboard_edge_thickness,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
        if self.clearance < 0:
            raise ValueError("clearance cannot be negative")
        if self.jig_length > self.fingerboard_length:
            raise ValueError("jig_length cannot exceed fingerboard_length")
        widest_cut = max(self.nut_width, self.bridge_width) + 2 * self.clearance
        if widest_cut >= 2 * self.radius:
            raise ValueError(
                "The cradle width, including clearance, must be less than "
                "the cylinder diameter"
            )


@dataclass(frozen=True)
class JigModel:
    jig: Part
    foam: Part
    fingerboard: Part
    block_length: float
    block_width: float
    block_height: float
    cradle_depth: float


def circular_sagitta(radius: float, chord_width: float) -> float:
    """Return the rise from a chord edge to the centre of a circle."""

    return radius - sqrt(radius**2 - (chord_width / 2) ** 2)


def make_jig(params: JigParameters | None = None) -> JigModel:
    """Build the jig and retain the removed volume for visualisation."""

    if params is None:
        params = JigParameters()
    params.validate()

    cut_length = params.fingerboard_length + 2 * params.clearance
    cut_nut_width = params.nut_width + 2 * params.clearance
    cut_bridge_width = params.bridge_width + 2 * params.clearance
    widest_cut = max(cut_nut_width, cut_bridge_width)
    end_inset = (cut_length - params.jig_length) / 2
    cut_width_delta = cut_bridge_width - cut_nut_width
    support_nut_width = (
        cut_nut_width + cut_width_delta * end_inset / cut_length
    )
    support_bridge_width = (
        cut_bridge_width - cut_width_delta * end_inset / cut_length
    )

    widest_sagitta = circular_sagitta(params.radius, widest_cut)
    hard_cradle_radius = params.radius + params.foam_thickness
    cylinder_centre_z = params.base_thickness + hard_cradle_radius
    board_surface_low_z = params.base_thickness + params.foam_thickness
    cradle_depth = widest_sagitta
    block_height = board_surface_low_z + cradle_depth
    # The cylindrical cut opens through both ends: there are no raised stops.
    block_length = params.jig_length
    block_width = widest_cut + 2 * params.side_wall

    block = Box(
        block_length,
        block_width,
        block_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # A 5 mm normal offset from a radius-55 surface is radius 60.  Keeping the
    # cylinders concentric makes the foam uniformly thick, while the hard
    # cradle retains base_thickness beneath its lowest line.
    cylinder = (
        Pos(0, 0, cylinder_centre_z)
        * Rot(0, 90, 0)
        * Cylinder(
            hard_cradle_radius,
            cut_length + 2.0,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
    )

    # Loft two vertical rectangles to limit the cylindrical cut to the
    # tapered plan-view outline of the fingerboard.
    nut_plane = Plane(
        origin=(-cut_length / 2, 0, cylinder_centre_z),
        x_dir=(0, 1, 0),
        z_dir=(1, 0, 0),
    )
    bridge_plane = Plane(
        origin=(cut_length / 2, 0, cylinder_centre_z),
        x_dir=(0, 1, 0),
        z_dir=(1, 0, 0),
    )
    nut_profile = nut_plane * Rectangle(
        cut_nut_width,
        2 * hard_cradle_radius,
        align=(Align.CENTER, Align.CENTER),
    )
    bridge_profile = bridge_plane * Rectangle(
        cut_bridge_width,
        2 * hard_cradle_radius,
        align=(Align.CENTER, Align.CENTER),
    )
    tapered_limit = loft([nut_profile, bridge_profile])

    # The parallel vice block stops at the lowest point of the cradle.  Only
    # the tapered cylindrical support rises above it, so there is no side lip
    # and an oversized foam sheet may hang over either edge.
    support_profile_height = block_height + 2.0
    support_nut_plane = Plane(
        origin=(-block_length / 2, 0, support_profile_height / 2),
        x_dir=(0, 1, 0),
        z_dir=(1, 0, 0),
    )
    support_bridge_plane = Plane(
        origin=(block_length / 2, 0, support_profile_height / 2),
        x_dir=(0, 1, 0),
        z_dir=(1, 0, 0),
    )
    support_limit = loft(
        [
            support_nut_plane
            * Rectangle(
                support_nut_width,
                support_profile_height,
                align=(Align.CENTER, Align.CENTER),
            ),
            support_bridge_plane
            * Rectangle(
                support_bridge_width,
                support_profile_height,
                align=(Align.CENTER, Align.CENTER),
            ),
        ]
    )
    central_support = (block & support_limit) - cylinder
    vice_base = Box(
        block_length,
        block_width,
        params.base_thickness,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    jig = vice_base.fuse(central_support)

    # Uniform foam layer between the hard radius and the fingerboard radius.
    board_surface_cylinder = (
        Pos(0, 0, cylinder_centre_z)
        * Rot(0, 90, 0)
        * Cylinder(
            params.radius,
            cut_length + 2.0,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
    )
    foam_clip = Box(
        cut_length,
        block_width,
        block_height + 1.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    foam = (cylinder - board_surface_cylinder) & tapered_limit & foam_clip

    # Nominal fingerboard ghost.  Its curved contact face is exact; the upper
    # face uses an editable nominal edge thickness because it will be planed.
    board_nut_plane = Plane(
        origin=(-params.fingerboard_length / 2, 0, cylinder_centre_z),
        x_dir=(0, 1, 0),
        z_dir=(1, 0, 0),
    )
    board_bridge_plane = Plane(
        origin=(params.fingerboard_length / 2, 0, cylinder_centre_z),
        x_dir=(0, 1, 0),
        z_dir=(1, 0, 0),
    )
    board_taper = loft(
        [
            board_nut_plane
            * Rectangle(
                params.nut_width,
                2 * params.radius,
                align=(Align.CENTER, Align.CENTER),
            ),
            board_bridge_plane
            * Rectangle(
                params.bridge_width,
                2 * params.radius,
                align=(Align.CENTER, Align.CENTER),
            ),
        ]
    )
    curved_board_volume = board_surface_cylinder & board_taper

    nut_top_z = (
        board_surface_low_z
        + circular_sagitta(params.radius, params.nut_width)
        + params.fingerboard_edge_thickness
    )
    bridge_top_z = (
        board_surface_low_z
        + circular_sagitta(params.radius, params.bridge_width)
        + params.fingerboard_edge_thickness
    )
    cap_height = 2 * hard_cradle_radius
    nut_cap_plane = Plane(
        origin=(
            -params.fingerboard_length / 2,
            0,
            nut_top_z - cap_height / 2,
        ),
        x_dir=(0, 1, 0),
        z_dir=(1, 0, 0),
    )
    bridge_cap_plane = Plane(
        origin=(
            params.fingerboard_length / 2,
            0,
            bridge_top_z - cap_height / 2,
        ),
        x_dir=(0, 1, 0),
        z_dir=(1, 0, 0),
    )
    board_top_limit = loft(
        [
            nut_cap_plane
            * Rectangle(
                params.nut_width,
                cap_height,
                align=(Align.CENTER, Align.CENTER),
            ),
            bridge_cap_plane
            * Rectangle(
                params.bridge_width,
                cap_height,
                align=(Align.CENTER, Align.CENTER),
            ),
        ]
    )
    fingerboard = curved_board_volume & board_top_limit

    for name, part in (("jig", jig), ("foam", foam), ("fingerboard", fingerboard)):
        if len(part.solids()) != 1 or not part.is_valid:
            raise RuntimeError(f"The requested parameters did not produce a valid {name}")

    return JigModel(
        jig=jig,
        foam=foam,
        fingerboard=fingerboard,
        block_length=block_length,
        block_width=block_width,
        block_height=jig.bounding_box().size.Z,
        cradle_depth=cradle_depth,
    )


def show_in_ocp_viewer(model: JigModel) -> None:
    """Send the jig, foam, and fingerboard ghosts to OCP CAD Viewer."""

    try:
        from ocp_vscode import Camera, show
    except ImportError as exc:
        raise RuntimeError(
            "OCP Viewer support needs ocp-vscode: pip install ocp-vscode"
        ) from exc

    show(
        model.jig,
        model.foam,
        model.fingerboard,
        names=["jig", "5 mm foam", "fingerboard (nominal)"],
        colors=["lightgray", "orange", "saddlebrown"],
        alphas=[1.0, 0.55, 0.25],
        reset_camera=Camera.RESET,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius", type=float, default=55.0)
    parser.add_argument("--length", type=float, default=256.0)
    parser.add_argument("--jig-length", type=float, default=250.0)
    parser.add_argument("--nut-width", type=float, default=42.0)
    parser.add_argument("--bridge-width", type=float, default=62.0)
    parser.add_argument("--clearance", type=float, default=0.25)
    parser.add_argument("--side-wall", type=float, default=8.0)
    parser.add_argument("--base-thickness", type=float, default=30.0)
    parser.add_argument("--foam-thickness", type=float, default=5.0)
    parser.add_argument("--fingerboard-edge-thickness", type=float, default=6.0)
    parser.add_argument("--output", type=Path, default=Path("build/fingerboard_jig"))
    parser.add_argument("--show", action="store_true", help="show in OCP CAD Viewer")
    parser.add_argument("--no-export", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    params = JigParameters(
        radius=args.radius,
        fingerboard_length=args.length,
        jig_length=args.jig_length,
        nut_width=args.nut_width,
        bridge_width=args.bridge_width,
        clearance=args.clearance,
        side_wall=args.side_wall,
        base_thickness=args.base_thickness,
        foam_thickness=args.foam_thickness,
        fingerboard_edge_thickness=args.fingerboard_edge_thickness,
    )
    model = make_jig(params)

    print(
        f"Jig: {model.block_length:.2f} x {model.block_width:.2f} x "
        f"{model.block_height:.2f} mm"
    )
    print(f"Cylindrical rise at widest cleared width: {model.cradle_depth:.2f} mm")
    print(f"Hard cradle radius: {params.radius + params.foam_thickness:.2f} mm")

    if not args.no_export:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        stl_path = args.output.with_suffix(".stl")
        step_path = args.output.with_suffix(".step")
        export_stl(model.jig, str(stl_path), tolerance=0.01, angular_tolerance=0.1)
        export_step(model.jig, str(step_path))
        print(f"Exported {stl_path} and {step_path}")

    if args.show:
        show_in_ocp_viewer(model)


if __name__ == "__main__":
    main()
