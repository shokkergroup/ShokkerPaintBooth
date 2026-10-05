"""X LAB — thirty owner-authorized material experiments for the live SHOKKER lab.

SPB-105 / X-LAB-1, 2026-08-28. Owner granted Codex carte blanche: build a
category that reaches beyond existing families, without palette-only variants,
noise filler, macro icons or copied carriers.  The shared code below is only a
runtime adapter and physical packing discipline.  Each recipe chooses a
different material process (flow, optical thickness, caustic, ceramic stress,
ferrofluid, vapor, carbon, etc.) and its own field topology/palette.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock

import cv2
import numpy as np


# Native delivery canvas.  X LAB's controlled micro-events are authored at the
# real 2048² scale so the M/R/Cc edge response survives instead of being
# softened by an upsampled 1024 proxy.
WORK = 2048
GROUP = "X LAB"
_CACHE: OrderedDict[str, tuple[np.ndarray, np.ndarray]] = OrderedDict()
_LOCK = RLock()


@dataclass(frozen=True)
class Recipe:
    fid: str
    name: str
    swatch: str
    story: str
    family: int
    palette: tuple[tuple[float, float, float], ...]
    p: tuple[float, float, float, float]


# Every row is a separate material proposition, not a renamed colorway.
RECIPES = (
    Recipe("xlab_abyssal_lens", "Abyssal Lens", "#061A3A", "pressure-warped deep-sea glass with blue caustic lenses", 0, ((.002,.008,.020),(.00,.18,.42),(.02,.72,.92),(.64,.92,1.0)), (7.3,13.1,.44,.22)),
    Recipe("xlab_afterimage_lacquer", "Afterimage Lacquer", "#FF3EA5", "persistent magenta/cyan light trails trapped under black clear", 4, ((.006,.004,.014),(.18,.02,.25),(.96,.03,.49),(.08,.88,1.0)), (9.1,21.7,.31,.63)),
    Recipe("xlab_aerogel_fire", "Aerogel Fire", "#F0C070", "weightless amber heat suspended in frosted silica", 3, ((.012,.014,.020),(.12,.16,.22),(.96,.38,.03),(1.0,.92,.66)), (6.2,17.8,.56,.19)),
    Recipe("xlab_anamorphic_pearl", "Anamorphic Pearl", "#F4E8FF", "elongated pearl interference that turns with the surface", 5, ((.025,.020,.040),(.26,.12,.45),(.82,.56,.94),(.80,.98,1.0)), (11.4,29.2,.66,.42)),
    Recipe("xlab_anti_gravity_foil", "Anti-Gravity Foil", "#B0FFB8", "levitating mint/gold foil planes with impossible shadow direction", 1, ((.004,.012,.012),(.04,.28,.20),(.48,.98,.54),(1.0,.78,.24)), (8.8,19.1,.35,.72)),
    Recipe("xlab_arc_weld_velvet", "Arc-Weld Velvet", "#70A8FF", "blue arc scars crossing soft black velvet chrome", 4, ((.004,.006,.012),(.03,.07,.16),(.12,.48,.95),(.95,.98,1.0)), (12.8,25.4,.51,.38)),
    Recipe("xlab_black_ice_orbit", "Black Ice Orbit", "#153B66", "black ice rings and frozen orbital shear", 1, ((.002,.006,.013),(.02,.10,.24),(.08,.44,.78),(.78,.94,1.0)), (5.9,18.4,.72,.28)),
    Recipe("xlab_bloomglass", "Bloomglass", "#FF7BCB", "hot-pink glass blossoms arising from cool translucent fractures", 2, ((.008,.004,.016),(.17,.04,.28),(.88,.08,.55),(.30,.90,1.0)), (10.7,16.6,.43,.58)),
    Recipe("xlab_brunel_current", "Brunel Current", "#D68B4A", "copper engineering-current waves through black enamel", 3, ((.010,.008,.006),(.18,.07,.02),(.72,.23,.04),(1.0,.72,.26)), (7.8,22.8,.47,.33)),
    Recipe("xlab_caustic_engine", "Caustic Engine", "#2FFFF0", "machined cyan caustics with deep dark engine cavities", 0, ((.002,.012,.016),(.00,.20,.25),(.00,.86,.74),(.88,1.0,.90)), (13.4,31.1,.39,.61)),
    Recipe("xlab_ceramic_storm", "Ceramic Storm", "#D5E5FF", "white ceramic tension cracks carrying electric blue glaze", 3, ((.014,.016,.020),(.18,.22,.30),(.32,.58,.96),(.90,.96,1.0)), (6.7,14.3,.68,.27)),
    Recipe("xlab_chiral_mercury", "Chiral Mercury", "#C6C9E8", "liquid mercury spiraling differently on each side of the sheet", 0, ((.005,.006,.012),(.12,.13,.23),(.56,.59,.82),(.94,.96,1.0)), (9.9,26.2,.55,.49)),
    Recipe("xlab_chromatophore", "Chromatophore", "#6AFF9B", "living color cells that bloom and retract beneath a glossy skin", 2, ((.004,.012,.010),(.03,.20,.12),(.10,.84,.38),(.78,1.0,.54)), (12.1,23.6,.38,.66)),
    Recipe("xlab_cinder_mirror", "Cinder Mirror", "#FF5A22", "mirror-black ash plate cut by incandescent cinder veins", 3, ((.008,.006,.006),(.14,.025,.008),(.92,.12,.012),(1.0,.72,.30)), (8.1,27.5,.49,.24)),
    Recipe("xlab_coral_voltage", "Coral Voltage", "#FF6F92", "electric coral growth branching inside clear pink resin", 2, ((.010,.004,.012),(.24,.02,.13),(.94,.12,.38),(.60,.96,.88)), (14.2,30.3,.57,.34)),
    Recipe("xlab_cryogenic_sunset", "Cryogenic Sunset", "#9FCBFF", "ice-blue metal flash crossed by a single impossible warm horizon", 5, ((.004,.010,.020),(.04,.19,.38),(.24,.72,.98),(1.0,.38,.12)), (5.6,20.9,.61,.51)),
    Recipe("xlab_deep_time", "Deep Time", "#7250B8", "mineral time-lapse bands pressed into a violet-black geological clear", 3, ((.009,.006,.016),(.11,.04,.22),(.42,.18,.72),(.96,.68,.42)), (4.9,12.7,.74,.31)),
    Recipe("xlab_dichroic_skin", "Dichroic Skin", "#D35CFF", "thin dichroic skin switching cyan, violet and hot gold at its folds", 5, ((.006,.004,.014),(.12,.02,.24),(.70,.14,.95),(.00,.84,.94),(1.0,.72,.16)), (10.2,24.4,.46,.59)),
    Recipe("xlab_electric_ink", "Electric Ink", "#1D8BFF", "conductive blue ink spreading in precise capillary rivers", 4, ((.003,.007,.016),(.01,.10,.30),(.03,.42,.94),(.78,.96,1.0)), (15.1,34.6,.33,.71)),
    Recipe("xlab_ferrofluid_silk", "Ferrofluid Silk", "#4C2A6D", "black ferrofluid spikes folded into violet satin", 0, ((.003,.002,.008),(.08,.02,.15),(.38,.10,.62),(.92,.58,1.0)), (11.9,18.2,.63,.37)),
    Recipe("xlab_ghost_transmission", "Ghost Transmission", "#DDF7FF", "pale transmission lines fading in and out of smoked blue glass", 1, ((.004,.008,.012),(.06,.18,.24),(.34,.74,.82),(.90,1.0,1.0)), (7.1,28.7,.40,.55)),
    Recipe("xlab_hologram_metal", "Hologram Metal", "#7AFFE8", "hard metallic hologram plates with impossible spectral refraction", 1, ((.004,.010,.012),(.04,.25,.24),(.10,.92,.68),(.84,.36,1.0)), (13.8,22.1,.52,.41)),
    Recipe("xlab_ion_bloom", "Ion Bloom", "#A759FF", "violet ion flowers expanding through conductive midnight", 2, ((.005,.003,.012),(.11,.02,.25),(.50,.10,.92),(.24,.86,1.0)), (9.4,26.9,.41,.64)),
    Recipe("xlab_laminar_magma", "Laminar Magma", "#FF8A20", "thin orange magma lamellae moving beneath obsidian clear", 3, ((.010,.004,.002),(.20,.025,.004),(.88,.14,.006),(1.0,.76,.16)), (12.3,33.7,.54,.29)),
    Recipe("xlab_luminous_carbon", "Luminous Carbon", "#6EFFE0", "carbon-like conductive ribs emitting a controlled seafoam glow", 5, ((.004,.010,.012),(.03,.16,.17),(.07,.58,.48),(.78,1.0,.88)), (16.2,37.5,.36,.62)),
    Recipe("xlab_memory_glass", "Memory Glass", "#E6A4FF", "glass remembers prior stress paths as lilac ghost reflections", 5, ((.010,.006,.016),(.20,.07,.28),(.70,.34,.88),(.96,.84,1.0)), (6.8,15.9,.69,.45)),
    Recipe("xlab_nebula_ceramic", "Nebula Ceramic", "#755BFF", "deep cobalt ceramic with embedded violet nebula firing clouds", 2, ((.004,.006,.020),(.05,.08,.32),(.30,.18,.90),(.86,.46,1.0)), (8.6,19.7,.58,.36)),
    Recipe("xlab_photon_patina", "Photon Patina", "#B6FF42", "acid-green photon oxidation crawling over old bronze metal", 3, ((.007,.010,.003),(.10,.13,.015),(.36,.62,.03),(.94,.96,.32)), (10.9,23.1,.44,.67)),
    Recipe("xlab_quantum_tide", "Quantum Tide", "#00CFFF", "blue quantum tide folding through a black tidal mirror", 0, ((.002,.008,.014),(.00,.14,.30),(.00,.62,.92),(.78,.96,1.0)), (14.6,32.3,.45,.53)),
    Recipe("xlab_sonic_chrome", "Sonic Chrome", "#FFDC66", "golden sonic pressure waves embossed in mirror chrome", 4, ((.008,.006,.002),(.20,.12,.012),(.86,.56,.04),(1.0,.94,.66)), (18.1,39.2,.29,.73)),
)
BY_ID = {recipe.fid: recipe for recipe in RECIPES}
STYLE_INDEX = {recipe.fid: index for index, recipe in enumerate(RECIPES)}


def _unit(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    return np.clip((a - lo) / max(hi - lo, 1e-7), 0.0, 1.0)


def _ridge(phase: np.ndarray, width: float) -> np.ndarray:
    d = np.abs(np.mod(phase + .5, 1.0) - .5)
    return np.exp(-((d / width) ** 2))


def _palette(field: np.ndarray, colors: tuple[tuple[float, float, float], ...]) -> np.ndarray:
    p = np.mod(field, 1.0) * len(colors)
    low = np.floor(p).astype(np.int16)
    t = (p - low)[..., None]
    c = np.asarray(colors, np.float32)
    return c[low] * (1.0 - t) + c[(low + 1) % len(c)] * t


def _ramp(field: np.ndarray, colors: tuple[tuple[float, float, float], ...]) -> np.ndarray:
    """Ordered material palette: an optical material is not a rainbow loop."""
    c = np.asarray(colors, np.float32)
    p = np.clip(field, 0.0, 1.0) * (len(c) - 1)
    low = np.minimum(np.floor(p).astype(np.int16), len(c) - 2)
    t = (p - low)[..., None]
    return c[low] * (1.0 - t) + c[low + 1] * t


def _coords() -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    return (x / (WORK - 1)) * 2.0 - 1.0, (y / (WORK - 1)) * 2.0 - 1.0


def _xlab_fields(style: int, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Thirty separate small-feature material grammars.

    SPB-105 / X-LAB-1. The first contact shared too many ripples. This is a
    deliberate replacement before any live thumbnail promotion: each index is
    a different physical proposition, with all visible detail kept fine at
    native resolution rather than enlarged into a logo-sized motif.
    """
    if style == 0:  # Abyssal Lens — pressured water sheet / caustic lenses
        u=x+.15*np.sin(5*y+.8*np.sin(9*x)); v=y+.12*np.sin(7*x)
        body=_unit(.5+.20*np.sin(12*u+5*v)+.16*np.sin(20*v-4*u)); fine=_ridge(48*u+14*v,.075); lip=_ridge(3.1*body+.16*u,.045)
    elif style == 1:  # Afterimage Lacquer — persistent light trails
        u=.83*x+.56*y+.035*np.sin(21*y); v=-.56*x+.83*y
        gate=.36+.64*_ridge(7*v+.4*np.sin(3*u),.20)
        body=np.clip(.32+.42*_ridge(17*u,.16)*gate+.18*_ridge(34*u+.25*v,.07),0.0,1.0); fine=_ridge(88*u+9*v,.065)*gate; lip=_ridge(9*u,.055)
    elif style == 2:  # Aerogel Fire — silica chambers carrying heat
        u=x+.055*np.sin(12*y); v=y+.055*np.sin(9*x)
        body=_unit(.36+.32*np.maximum(np.cos(31*u),np.cos(27*v))+.20*np.sin(9*u*v)); fine=np.maximum(_ridge(66*u,.06),_ridge(61*v,.06)); lip=_ridge(9*(u+v),.07)
    elif style == 3:  # Anamorphic Pearl — individual pearl cells, not stripes
        u=.83*x+.56*y; v=-.56*x+.83*y; density=36.0
        fu=np.mod((u+1.5)*density,1.0)-.5; fv=np.mod((v+1.5)*density,1.0)-.5
        radius=np.sqrt(fu*fu+fv*fv); phase=.5+.5*np.sin(3.2*u-2.1*v+.35*np.sin(4*v))
        # The tile centres carry the pearl; their rims are soft, interrupted
        # optical shoulders. This removes the old uninterrupted vertical lines.
        body=np.clip(.25+.48*np.exp(-((radius-.18)/.20)**2)+.18*phase,0.0,1.0)
        fine=np.exp(-((radius-.30)/.055)**2)*(.35+.65*phase)
        lip=.18*np.exp(-((radius-.47)/.030)**2)
    elif style == 4:  # Anti-Gravity Foil — faceted planes / displaced shadow
        # SPB-105 / XLAB-FOIL-I3/I4, 2026-08-29 — two small-facet trials
        # were rejected: both read as a uniform green lattice at picker
        # scale and each exceeded the 2–3s native budget. Preserve the
        # existing carrier until a genuinely different foil grammar wins.
        u=.72*x-.70*y; v=.70*x+.72*y; plane=np.abs(np.sin(16*u)+.58*np.sin(19*v))
        body=_unit(.18+.55*(plane>.82).astype(np.float32)+.18*np.sin(38*u*v)); fine=np.maximum(_ridge(58*u,.05),_ridge(54*v,.05)); lip=_ridge(16*u-9*v,.045)
    elif style == 5:  # Arc-Weld Velvet — seam through an absorbent void
        seam=y-.24*np.sin(3.4*x)-.07*np.sin(13*x)
        body=np.clip(.42+.42*np.exp(-(seam/.11)**2)+.16*np.exp(-((seam-.31)/.07)**2),0.0,1.0); fine=_ridge(77*x+11*np.sin(10*x),.06)*np.exp(-(seam/.22)**2); lip=_ridge(18*x,.06)*np.exp(-(seam/.12)**2)
    elif style == 6:  # Black Ice Orbit — brittle orbital lensing
        rr=np.sqrt((x+.14)**2+(y-.06)**2); q=rr+.065*np.sin(8*np.arctan2(y,x))
        body=_unit(.12+.46*_ridge(7.2*q,.10)+.25*np.sin(36*q)); fine=_ridge(61*q+5*np.arctan2(y,x),.055); lip=_ridge(13*q,.05)
    elif style == 7:  # Bloomglass — blown membranes, never generic cells
        u=x+.07*np.sin(8*y); v=y+.05*np.sin(9*x)
        body=_unit(.18+.42*np.sin(10*u)*np.sin(9*v)+.24*np.cos(19*(u*u+v*v))); fine=np.maximum(_ridge(50*(u+v),.065),_ridge(47*(u-v),.065)); lip=_ridge(6*(u*u+v*v),.08)
    elif style == 8:  # Brunel Current — cable engineering beneath enamel
        q=y+.16*np.sin(3*x)+.05*np.sin(13*x)
        body=np.clip(.22+.48*_ridge(5*q,.16)+.24*_ridge(13*q+.5*x,.09),0.0,1.0); fine=_ridge(72*q+8*x,.055); lip=_ridge(21*q,.05)
    elif style == 9:  # Caustic Engine — refraction through a machined grid
        u=x+.08*np.sin(7*y); v=y+.08*np.sin(8*x)
        body=_unit(.22+.28*np.sin(22*u)*np.sin(25*v)+.22*np.cos(17*(u+v))); fine=np.maximum(_ridge(68*u+.25*np.sin(9*v),.055),_ridge(73*v,.055)); lip=_ridge(17*(u-v),.055)
    elif style == 10:  # Ceramic Storm — tensile glaze, angular micro-cracks
        u=x+.07*np.sin(6*y); v=y+.06*np.sin(5*x)
        body=_unit(.62+.18*np.sin(14*u+3*v)+.12*np.cos(18*v-4*u)); fine=np.maximum(_ridge(43*u+17*v,.035),_ridge(51*u-12*v,.032)); lip=_ridge(11*u+7*v,.055)
    elif style == 11:  # Chiral Mercury — opposite-handed liquid rolls
        l=np.arctan2(y,x+.43); r=np.arctan2(y,x-.43)
        body=_unit(.30+.23*np.sin(18*(l+.23*np.log(np.sqrt((x+.43)**2+y*y)+.03)))+.23*np.sin(18*(r-.23*np.log(np.sqrt((x-.43)**2+y*y)+.03)))); fine=np.maximum(_ridge(55*l,.055),_ridge(55*r,.055)); lip=_ridge(8*(l-r),.06)
    elif style == 12:  # Chromatophore — packed pigment shutters
        u=x+.04*np.sin(17*y); v=y+.04*np.sin(19*x); cell=np.cos(31*u)+np.cos(27*(.5*u+.866*v))+np.cos(27*(-.5*u+.866*v))
        body=_unit(cell); fine=_ridge(36*body,.065); lip=_ridge(10*u-8*v,.07)
    elif style == 13:  # Cinder Mirror — ash mirror with incandescent cuts
        u=x+.08*np.sin(7*y); v=y+.05*np.sin(11*x); fracture=np.maximum(_ridge(17*u+8*v,.025),_ridge(23*u-13*v,.022))
        body=np.clip(.38+.46*fracture+.27*np.sin(34*u)*np.sin(31*v),0.0,1.0); fine=_ridge(78*u-41*v,.04)*fracture; lip=_ridge(12*u+4*v,.055)
    elif style == 14:  # Coral Voltage — conductive branching fan
        q=y-.18*np.sin(2.5*x); fan=np.abs(np.sin(10*x/(.18+np.abs(q))))
        body=_unit(.16+.46*np.exp(-(q/.55)**2)*fan+.16*np.sin(21*q)); fine=_ridge(58*x/(.22+np.abs(q)),.05)*np.exp(-(q/.62)**2); lip=_ridge(8*q,.065)
    elif style == 15:  # Cryogenic Sunset — frozen horizon refraction
        q=y+.045*np.sin(14*x)+.025*np.sin(41*x)
        body=_unit(.34+.26*np.sin(18*q)+.18*np.exp(-((q+.03)/.13)**2)+.10*x); fine=_ridge(76*q+3*x,.05); lip=_ridge(9*q,.07)
    elif style == 16:  # Deep Time — compressed mineral laminations
        q=y+.12*np.sin(2*x)+.035*np.sin(17*x)
        body=_unit(.28+.25*np.sin(13*q)+.20*np.sin(26*q+.4*x)+.11*np.cos(7*x)); fine=_ridge(68*q+.7*x,.05); lip=_ridge(7*q,.075)
    elif style == 17:  # Dichroic Skin — shifting diamond interference
        u=.707*(x+y); v=.707*(y-x)
        body=_unit(.30+.25*np.cos(19*u)*np.cos(19*v)+.18*np.sin(12*u-7*v)); fine=np.maximum(_ridge(64*u,.05),_ridge(64*v,.05)); lip=_ridge(13*(u+v),.06)
    elif style == 18:  # Electric Ink — capillary paths in wet substrate
        u=x+.13*np.sin(4*y); v=y+.06*np.sin(9*x); flow=np.sin(10*u+3*np.sin(5*v))-.52*np.sin(15*v)
        body=np.clip(.46+.36*np.exp(-((flow-.12)/.13)**2)+.12*np.sin(30*u),0.0,1.0); fine=_ridge(66*flow,.05); lip=_ridge(12*flow,.06)
    elif style == 19:  # Ferrofluid Silk — magnetics stretched as satin
        u=x+.04*np.sin(11*y); v=y+.11*np.sin(5*x); field=np.sin(25*u)+np.sin(25*v)+.4*np.sin(25*(u+v))
        body=_unit(.22+.32*np.abs(field)+.15*np.cos(7*u*v)); fine=_ridge(54*(u-v),.048); lip=_ridge(9*(u+v),.065)
    elif style == 20:  # Ghost Transmission — fading trace architecture
        u=x+.05*np.sin(5*y); v=y+.04*np.sin(7*x); paths=np.maximum(_ridge(15*u,.035)*_ridge(5*v,.16),_ridge(15*v,.035)*_ridge(5*u,.16))
        body=np.clip(.48+.36*paths+.12*np.sin(31*u*v),0.0,1.0); fine=np.maximum(_ridge(75*u,.045),_ridge(75*v,.045))*paths; lip=_ridge(12*(u+v),.07)
    elif style == 21:  # Hologram Metal — offset diffraction facets
        # SPB-105 / XLAB-HOLOGRAM-I2, 2026-08-29 — microprism prototype
        # rejected: it reduced to a decorative lattice and took 3.168s.
        # Keep prior carrier until a non-grid foil construction is stronger.
        u=.82*x+.57*y; v=-.57*x+.82*y; facets=np.abs(np.sin(12*u))+np.abs(np.sin(13*v))+np.abs(np.sin(11*(u+v)))
        body=_unit(facets); fine=np.maximum(_ridge(63*u,.045),_ridge(59*v,.045)); lip=_ridge(18*(u-v),.05)
    elif style == 22:  # Ion Bloom — electromagnetic flower fields
        u=x+.05*np.sin(8*y); v=y+.05*np.sin(8*x); rad=np.sqrt(u*u+v*v); petals=np.cos(9*np.arctan2(v,u))
        body=_unit(.26+.30*np.cos(24*rad+2*petals)+.19*petals); fine=_ridge(52*rad+5*petals,.05); lip=_ridge(10*rad,.07)
    elif style == 23:  # Laminar Magma — hot sheared lamellae
        q=y+.14*np.sin(4*x)+.04*np.sin(19*x)
        body=_unit(.20+.28*np.sin(15*q)+.23*np.sin(31*q+.7*x)+.10*np.cos(9*x)); fine=_ridge(74*q+2*x,.047); lip=_ridge(8*q,.07)
    elif style == 24:  # Luminous Carbon — conductive carbon tow
        u=.8*x+.6*y; v=-.6*x+.8*y; tow=np.maximum(_ridge(27*u,.11),_ridge(27*v+.45,.11))
        body=np.clip(.24+.66*tow+.14*np.sin(44*(u-v)),0.0,1.0); fine=np.maximum(_ridge(77*u,.045),_ridge(77*v,.045)); lip=_ridge(12*(u+v),.06)
    elif style == 25:  # Memory Glass — preserved stress scars
        u=x+.08*np.sin(8*y); v=y+.06*np.sin(6*x)
        body=_unit(.28+.24*np.sin(13*u+11*v)+.18*np.cos(22*u-17*v)); fine=np.maximum(_ridge(47*u+31*v,.028),_ridge(58*u-21*v,.028)); lip=_ridge(8*(u+v),.075)
    elif style == 26:  # Nebula Ceramic — cobalt fired mosaic / violet kiln glow
        u=x+.06*np.sin(9*y); v=y+.06*np.sin(7*x); mosaic=np.maximum(np.cos(18*u),np.cos(17*v))
        body=_unit(.28+.30*mosaic+.18*np.sin(29*u*v)); fine=np.maximum(_ridge(62*u,.05),_ridge(59*v,.05)); lip=_ridge(11*(u-v),.065)
    elif style == 27:  # Photon Patina — controlled oxide conversion
        u=x+.07*np.sin(7*y); v=y+.07*np.sin(5*x)
        body=_unit(.25+.22*np.sin(18*u)*np.sin(17*v)+.20*np.cos(13*(u-v))); fine=_ridge(57*body+9*u,.048); lip=_ridge(15*(u+v),.06)
    elif style == 28:  # Quantum Tide — coherent multi-axis interference
        u=x+.10*np.sin(5*y); v=y+.10*np.sin(6*x); phase=np.sin(23*u)+np.sin(19*v)+np.sin(17*(u+v))
        body=_unit(phase); fine=_ridge(64*body,.05); lip=_ridge(10*(u-v),.07)
    else:  # Sonic Chrome — acoustic diffraction in a gold mirror
        ang=np.arctan2(y+.14,x-.18); q=np.sqrt((x-.18)**2+(y+.14)**2)+.05*np.sin(7*ang)
        body=_unit(.26+.30*np.sin(29*q)+.18*np.cos(14*q+4*ang)); fine=_ridge(69*q+6*ang,.048); lip=_ridge(9*q,.07)
    return body.astype(np.float32), fine.astype(np.float32), lip.astype(np.float32)


def _local_material_cells(style: int, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Hard-transition, design-bound M/R/Cc states for tiled X LAB materials.

    SPB-105 / X-LAB-SPEC-2, 2026-08-28. Owner first contact: Anamorphic
    Pearl's every small square needs its own useful material state—Fractured
    pink in varying degrees beside flat, chrome and flake—not one generic
    continuous spec map. M7 prior pass 88.9–99.9 -> rerun pending.  The
    deterministic cell sequence is an authored placement rhythm, not grain or
    confetti; its 8–32px cells come from the corresponding visible geometry.
    """
    # Each selected material has a different coordinate basis and cell size,
    # so a local-state spec strengthens its own design instead of making X LAB
    # a secret second Fractured collection.
    if style == 3:       # Anamorphic Pearl: elongated rotated pearl squares.
        u, v, density = .83*x+.56*y, -.56*x+.83*y, 36.0
        palette = "fractured_pearl"
    elif style == 4:     # Anti-Gravity Foil: hard lifted foil planes.
        u, v, density = .72*x-.70*y, .70*x+.72*y, 30.0
        palette = "foil"
    elif style == 7:     # Bloomglass: glass panes retain their own clear state.
        u, v, density = x+.07*np.sin(8*y), y+.05*np.sin(9*x), 27.0
        palette = "glass"
    elif style == 12:    # Chromatophore: pigment shutters have local response.
        u, v, density = x+.04*np.sin(17*y), y+.04*np.sin(19*x), 34.0
        palette = "pigment"
    elif style == 21:    # Hologram Metal: facet-specific diffraction response.
        u, v, density = .82*x+.57*y, -.57*x+.82*y, 32.0
        palette = "hologram"
    elif style == 24:    # Luminous Carbon: conductive tow parcels.
        u, v, density = .80*x+.60*y, -.60*x+.80*y, 38.0
        palette = "carbon"
    elif style == 26:    # Nebula Ceramic: individual firing tiles.
        u, v, density = x+.06*np.sin(9*y), y+.06*np.sin(7*x), 29.0
        palette = "ceramic"
    else:
        raise ValueError(f"no local material cell palette for style {style}")

    cu = (u + 1.5) * density
    cv = (v + 1.5) * density
    gx, gy = np.floor(cu).astype(np.int32), np.floor(cv).astype(np.int32)
    fu, fv = np.mod(cu, 1.0), np.mod(cv, 1.0)
    # A repeatable placement cadence that visibly alternates states without
    # sampled noise; the broad grade controls where hot/cool variants travel.
    code = np.mod(17 * gx + 31 * gy + 3 * gx * gy, 16)
    state = np.mod(code + (np.sin(2.6*u - 1.9*v) > .15).astype(np.int32), 4)
    hot = np.sin(3.2*u - 2.1*v + .35*np.sin(4*v)) > 0.10
    edge = np.minimum(np.minimum(fu, 1.0-fu), np.minimum(fv, 1.0-fv)) < .075
    # Two-by-two 8–18px interior flake parcels are deliberately local to a
    # cell, never a layer of unrelated sparkle/grain.
    micro_u, micro_v = np.floor(fu * 2.0).astype(np.int32), np.floor(fv * 2.0).astype(np.int32)
    flake = np.mod(code + 5*micro_u + 7*micro_v, 7) == 0

    if palette == "fractured_pearl":
        # R + B high / G restrained produces the fused pink/magenta material
        # read the owner calls out, with cooler pinks toward the phase trough.
        # The states stay deliberately distinct, but their useful material
        # ranges track the visible pearl geometry instead of overpowering it.
        metal = np.select((state==0, state==1, state==2, hot), (216, 34, 176, 210), default=170)
        rough = np.select((state==0, state==1, state==2, hot), (28, 176, 108, 38), default=68)
        coat = np.select((state==0, state==1, state==2, hot), (184, 88, 150, 176), default=164)
    elif palette == "foil":
        metal = np.select((state==0, state==1, state==2, hot), (248, 34, 204, 232), default=174)
        rough = np.select((state==0, state==1, state==2, hot), (16, 174, 92, 42), default=70)
        coat = np.select((state==0, state==1, state==2, hot), (236, 58, 166, 208), default=128)
    elif palette == "glass":
        metal = np.select((state==0, state==1, state==2, hot), (226, 24, 158, 208), default=128)
        rough = np.select((state==0, state==1, state==2, hot), (22, 182, 96, 48), default=76)
        coat = np.select((state==0, state==1, state==2, hot), (250, 66, 190, 230), default=162)
    elif palette == "pigment":
        metal = np.select((state==0, state==1, state==2, hot), (214, 32, 172, 200), default=140)
        rough = np.select((state==0, state==1, state==2, hot), (30, 182, 118, 60), default=90)
        coat = np.select((state==0, state==1, state==2, hot), (182, 84, 152, 170), default=136)
    elif palette == "hologram":
        metal = np.select((state==0, state==1, state==2, hot), (250, 22, 206, 234), default=180)
        rough = np.select((state==0, state==1, state==2, hot), (14, 164, 84, 34), default=62)
        coat = np.select((state==0, state==1, state==2, hot), (248, 48, 184, 222), default=152)
    elif palette == "carbon":
        metal = np.select((state==0, state==1, state==2, hot), (220, 32, 166, 206), default=132)
        rough = np.select((state==0, state==1, state==2, hot), (32, 186, 104, 54), default=84)
        coat = np.select((state==0, state==1, state==2, hot), (176, 82, 150, 168), default=132)
    else:                # ceramic
        metal = np.select((state==0, state==1, state==2, hot), (210, 34, 158, 194), default=122)
        rough = np.select((state==0, state==1, state==2, hot), (34, 180, 124, 66), default=98)
        coat = np.select((state==0, state==1, state==2, hot), (186, 86, 154, 174), default=142)
    # Every tile has a crisp material border; flake is an interior state, not
    # a visual speckle pass. Edges catch a clear/metal shoulder.
    metal = np.where(edge, 224, metal); rough = np.where(edge, 34, rough); coat = np.where(edge, 188, coat)
    metal = np.where(flake & (state == 2), 224, metal)
    rough = np.where(flake & (state == 2), 72, rough)
    coat = np.where(flake & (state == 2), 168, coat)
    return np.stack((metal, rough, coat), axis=2).astype(np.uint8)


def _surface(recipe: Recipe) -> tuple[np.ndarray, np.ndarray]:
    """Create one intentional full-field material and independent M/R/Cc map."""
    x, y = _coords()
    a, b, c, d = recipe.p
    r = np.sqrt(x * x + y * y) + 1e-5
    ang = np.arctan2(y, x)
    # The six families have genuinely different causal histories. The recipe
    # values select one experiment inside that family, never a hue-only clone.
    if recipe.family == 0:  # advected liquid / ferrofluid / caustic
        qx = x + .14*np.sin(a*y + d*np.sin(b*x)) + .07*np.sin(c*9*x*y)
        qy = y + .13*np.sin(b*x - c*np.sin(a*y))
        body = _unit(.50 + .16*qx - .10*qy + .12*np.sin(a*qx + .55*b*qy) + .07*np.sin(b*qy - .7*a*qx))
        # Liquid systems get capillary fracture/shore anatomy, not a generic
        # stripe field. Each experiment changes its own advected shore map.
        fine = _unit(np.sqrt(sum(g*g for g in np.gradient(body.astype(np.float32)))))
        lip = _ridge(2.72*body + .18*np.sin(ang*a), .042)
        stress = _unit(np.abs(cv2.Laplacian(body.astype(np.float32), cv2.CV_32F)))
    elif recipe.family == 1:  # plates / orbits / hard optical geometry
        u = x*np.cos(c*np.pi) - y*np.sin(c*np.pi)
        v = x*np.sin(c*np.pi) + y*np.cos(c*np.pi)
        rings = np.sin(a*r + b*np.sin(2.0*ang + d))
        planes = np.abs(np.sin(b*u + .55*a*v + d*np.sin(a*v)))
        body = _unit(.55*rings + .45*planes + .18*np.sin(a*(u+v)))
        # Hard optical systems use intersecting plate cuts rather than waves.
        fine = np.maximum(_ridge((5.0+c*4.0)*u + .16*rings, .10), _ridge((4.0+d*3.0)*v - .12*planes, .10))
        lip = _ridge(2.48*body + .11*planes, .040)
        stress = _unit(np.abs(cv2.Laplacian(body.astype(np.float32), cv2.CV_32F)))
    elif recipe.family == 2:  # living cells / coral / bloom systems
        centers = ((-.64,-.48),(-.18,-.62),(.31,-.43),(.70,-.12),(-.55,.15),(.02,.08),(.48,.34),(-.25,.57),(.68,.66))
        field = np.zeros_like(x)
        for i, (cx, cy) in enumerate(centers):
            dx, dy = x-cx, y-cy
            dist = np.sqrt(dx*dx + (1.25+0.15*np.sin(i+a))*dy*dy)
            field += (0.48+0.06*(i%4))*np.cos((a*.65+i*.37)*dist + b*.12*i)
        body = _unit(field + .22*np.sin(b*x - a*y) + .13*np.sin((a+b)*(x*y)))
        # Cell membranes follow the locally generated biology rather than a
        # universal scanline overlay.
        fine = _unit(np.sqrt(sum(g*g for g in np.gradient(body.astype(np.float32))))) * (.30+.70*body)
        lip = _ridge(2.90*body + .15*np.sin(a*x), .043)
        stress = _unit(np.abs(cv2.Laplacian(body.astype(np.float32), cv2.CV_32F)))
    elif recipe.family == 3:  # fired ceramic / magma / geological material
        shear = x + .16*np.sin(a*y) + .06*np.sin(b*y + c*x)
        strata = .52 + .22*np.sin(a*shear + .5*np.sin(b*y)) + .13*np.sin(b*y - .7*a*x)
        body = _unit(strata + .12*np.sin((a+b)*x*y) + .10*np.sin(2.2*a*y))
        fine = np.maximum(_ridge((13+3*c)*shear + .6*np.sin(b*y), .12), _ridge((8+4*d)*y + .3*body, .15))
        lip = _ridge(2.36*body + .16*np.sin(b*shear), .040)
        stress = _unit(np.abs(cv2.Laplacian(body.astype(np.float32), cv2.CV_32F)))
    elif recipe.family == 4:  # signal, ink, weld and sonic pressure
        warp = x + .12*np.sin(a*y + d*np.sin(b*x))
        pulse = np.sin(a*warp + .24*np.sin(b*y))
        envelope = .34 + .66*np.exp(-((y - .24*np.sin(c*x))/.62)**2)
        body = _unit(.55*pulse*envelope + .35*np.sin(b*y - .55*a*x) + .16*np.sin((a+b)*x*y))
        fine = _ridge((24+9*c)*warp + (7+4*d)*y + 1.8*body, .11) * envelope
        lip = _ridge(2.68*body + .10*np.sin(a*y), .038)
        stress = _unit(np.abs(cv2.Laplacian(body.astype(np.float32), cv2.CV_32F)))
    else:  # anisotropic pearl, glass, carbon and dichroic skins
        twist = ang + .22*np.sin(a*r + d*np.sin(b*ang))
        stream = x*np.cos(twist) + y*np.sin(twist)
        body = _unit(.50 + .19*np.sin(a*stream + .7*np.sin(b*r)) + .14*np.sin(b*r - c*ang) + .10*np.cos((a+b)*x*y))
        fine = _ridge((28+8*c)*stream + (9+5*d)*r + .18*np.sin(a*ang), .12)
        lip = _ridge(2.58*body + .14*np.cos(b*ang), .040)
        stress = _unit(np.abs(cv2.Laplacian(body.astype(np.float32), cv2.CV_32F)))

    # _xlab_fields intentionally supersedes the prototype family composer.
    # The prototype established API/spec behavior but failed the owner-eye
    # diversity screen; this specific rebuild is the visual authority.
    body, fine, lip = _xlab_fields(STYLE_INDEX[recipe.fid], x, y)
    stress = _unit(np.abs(cv2.Laplacian(body, cv2.CV_32F)))
    pooled = np.exp(-((body-.55)/.19)**2) * (1.0-.45*stress)
    color = _ramp(np.clip(.82*body + .10*fine + .08*lip, 0.0, 1.0), recipe.palette)
    black = np.asarray(recipe.palette[0], np.float32)
    paint = black + color*(.16+.50*body)[...,None]
    # Style-owned highlight budgets prevent every X LAB material becoming the
    # same neon contour drawing. Bright optical lips are reserved for the
    # causal materials that actually have an exposed seam or interference rim.
    fine_weight = (.05,.15,.04,.08,.03,.11,.06,.04,.10,.05,.04,.05,.03,.13,.10,.06,.06,.05,.10,.03,.12,.06,.08,.07,.05,.06,.05,.04,.06,.06)[STYLE_INDEX[recipe.fid]]
    lip_weight = (.08,.10,.02,.07,.04,.14,.10,.07,.08,.08,.04,.06,.05,.15,.09,.05,.03,.04,.10,.07,.08,.05,.10,.07,.04,.08,.04,.06,.06,.10)[STYLE_INDEX[recipe.fid]]
    paint += color*(.16*pooled + fine_weight*fine)[...,None]
    paint += np.asarray((.88,.94,1.0),np.float32)*(lip_weight*lip)[...,None]
    paint = np.clip(paint, 0.0, 1.0).astype(np.float32)

    # Causal but non-inverse physical responses: exposed/order lip metal,
    # strained fine anatomy roughness, and mid-depth pooled clearcoat.
    metal = _unit(.52*(1-body) + .22*lip + .15*stress + .11*fine)
    rough = _unit(.40*stress + .31*fine + .17*lip + .12*(1-pooled))
    coat = _unit(.58*pooled + .25*body + .19*lip - .16*fine)
    # Ten real material strata per channel.  X LAB is intentionally not a
    # binary full-range look: metal carries the broadest substrate travel,
    # roughness carries abrasion range, and clearcoat has a controlled optical
    # shoulder.  All remain visibly multi-tiered/independent, but their spans
    # now match the fine paint density instead of yelling three 0–255 maps
    # underneath a quiet surface (the rejected M5 coherence result).
    m_levels = np.asarray((20,42,66,92,119,147,174,199,222,240),np.uint8)
    r_levels = np.asarray((24,42,61,83,106,128,149,169,184,194),np.uint8)
    c_levels = np.asarray((65,76,87,98,109,120,132,143,154,165),np.uint8)
    cuts = np.asarray((.07,.15,.24,.34,.45,.57,.69,.81,.91),np.float32)
    style = STYLE_INDEX[recipe.fid]
    if style in {3, 4, 7, 12, 21, 24, 26}:
        spec = _local_material_cells(style, x, y)
    else:
        spec = np.stack((m_levels[np.digitize(metal,cuts)], r_levels[np.digitize(rough,cuts)], c_levels[np.digitize(coat,cuts)]),axis=2)
    return paint, spec


def arrays(fid: str) -> tuple[np.ndarray, np.ndarray]:
    if fid not in BY_ID:
        raise KeyError(fid)
    with _LOCK:
        if fid in _CACHE:
            _CACHE.move_to_end(fid)
            return _CACHE[fid]
        paint, spec = _surface(BY_ID[fid])
        paint.setflags(write=False); spec.setflags(write=False)
        _CACHE[fid] = (paint, spec)
        while len(_CACHE) > 5:
            _CACHE.popitem(last=False)
        return paint, spec


def _mask(mask, h: int, w: int) -> np.ndarray:
    value = np.asarray(mask, np.float32)
    if value.ndim == 3: value = value[...,0]
    if value.shape != (h,w): value = cv2.resize(value,(w,h),interpolation=cv2.INTER_LINEAR)
    return np.clip(value,0,1)


def _pair(fid: str):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        del seed, bb
        h,w = int(shape[0]),int(shape[1]); src=np.asarray(paint,np.float32)[...,:3]
        if src.max(initial=0)>1.5: src=src/255.0
        if src.shape[:2] != (h,w): src=cv2.resize(src,(w,h),interpolation=cv2.INTER_LINEAR)
        authored,_ = arrays(fid)
        if authored.shape[:2] != (h,w): authored=cv2.resize(authored,(w,h),interpolation=cv2.INTER_CUBIC)
        mix=(_mask(mask,h,w)*float(pm))[...,None]
        return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)
    def spec_fn(shape, mask, seed, sm):
        del seed,sm
        h,w=int(shape[0]),int(shape[1]); _,packed=arrays(fid)
        if packed.shape[:2] != (h,w): packed=cv2.resize(packed,(w,h),interpolation=cv2.INTER_NEAREST)
        coverage=_mask(mask,h,w)[...,None]; out=np.empty((h,w,4),np.uint8)
        out[...,:3]=(packed.astype(np.float32)*coverage).astype(np.uint8); out[...,3]=(coverage[...,0]*255).astype(np.uint8)
        return out
    for fn in (paint_fn,spec_fn): fn._spb_mono_contract_wrapped=True
    return spec_fn,paint_fn


LIVE_PAIRS={recipe.fid:_pair(recipe.fid) for recipe in RECIPES}

def install_into_engine(mono_reg, base_reg=None, fusion_reg=None):
    del base_reg, fusion_reg
    mono_reg.update(LIVE_PAIRS)
    return f"x-lab-2026: {len(LIVE_PAIRS)} independent monolithic materials live"
