#!/usr/bin/env python
__version__ = "1.0"
#made by Gemini Pro on 21-April-2-26
import math
import sys
import argparse

def generate_fefco_0427_svg(length_in, width_in, height_in, thickness, filename):
    # Inside dimensions (Target)
    L_in = float(length_in)
    W_in = float(width_in)
    H_in = float(height_in)
    t = float(thickness)
    
    # Calculate Base Panel Dimensions (Bottom panel)
    # The length must accommodate the double folded side walls (2*t on left, 2*t on right)
    L_bot = L_in + 4 * t
    # The width must accommodate the single front and back walls (1*t front, 1*t back)
    W_bot = W_in + 2 * t
    
    # Clearance values
    c = t * 1.5
    
    # Heights of panels
    H_side = H_in + t      # Outer side wall (needs to cover inner + top fold)
    gap = 2 * t            # The rollover gap at the top of the side walls
    H_inner = H_in - t     # Inner side wall
    
    H_front = H_in + t
    H_back = H_in + t
    L_lid = L_bot - 2 * t  # Lid fits inside the double walls
    W_lid = W_bot + t      # Lid top cover depth
    H_tuck = max(15.0, H_in - 3 * t) # Front tuck flap
    
    # Dust Flap length
    FlapLength = max(20.0, W_bot / 2.0 - 2 * t)
    
    # Y-coordinates of main horizontal fold lines
    y1 = -H_front                          # Bottom edge of Front panel
    y2 = 0.0                               # Fold: Front to Bottom
    y3 = W_bot                             # Fold: Bottom to Back
    y4 = W_bot + H_back                    # Fold: Back to Lid
    y5 = y4 + W_lid                        # Fold: Lid to Tuck Flap
    y6 = y5 + H_tuck                       # Top edge of Tuck Flap
    
    # X-coordinates of main vertical fold lines
    x_L_out1 = -H_side
    x_L_out2 = -H_side - gap
    x_L_end  = -H_side - gap - H_inner
    
    x_R_out1 = L_bot + H_side
    x_R_out2 = L_bot + H_side + gap
    x_R_end  = L_bot + H_side + gap + H_inner
    
    # Tab locking mechanism sizes
    tab_ext = 2.4 * t  # Extended by 20% (was 2.0 * t)
    tab_w = max(10.0, min(30.0, W_bot / 5.0))
    
    if W_bot > 80.0:
        d_tab = W_bot / 6.0
        tabs = [
            (y2 + d_tab - tab_w / 2.0, y2 + d_tab + tab_w / 2.0),
            (y3 - d_tab - tab_w / 2.0, y3 - d_tab + tab_w / 2.0)
        ]
    else:
        y_mid = W_bot / 2.0
        tabs = [
            (y_mid - tab_w / 2.0, y_mid + tab_w / 2.0)
        ]

    # --- PERIMETER PATH (CUTS) ---
    pts = []
    
    # 1. Lid Tuck Flap Top
    pts.append((2 * t, y6))
    pts.append((L_bot - 2 * t, y6))
    
    # 2. Lid Tuck Flap Right (with locking ear)
    ear_len = min(15.0, H_tuck / 2.0)
    ear_taper_y = y5 + ear_len + min(5.0, H_tuck / 4.0)
    pts.append((L_bot - 2 * t, ear_taper_y))
    pts.append((L_bot - 0.5 * t, y5 + ear_len))
    pts.append((L_bot - 0.5 * t, y5 + 2 * t))
    pts.append((L_bot - t, y5))
    
    # 3. Lid Right Edge
    pts.append((L_bot - t, y4))
    
    # 4. Back Panel Right Corner offset & Back Dust Flap
    pts.append((L_bot, y4))
    pts.append((L_bot + FlapLength, y4 - 2 * t))
    pts.append((L_bot + FlapLength, y3 + 2 * t))
    pts.append((L_bot, y3))
    
    # 5. Right Outer & Inner Side Top Edge
    pts.append((x_R_out2, y3))
    pts.append((x_R_end, y3 - c))
    
    # 6. Right Inner Side Right Edge (with 20% longer tabs)
    for (tbot, ttop) in reversed(tabs):
        tab_taper = min(t, (ttop - tbot) / 4.0)
        pts.append((x_R_end, ttop))
        pts.append((x_R_end + tab_ext, ttop - tab_taper))
        pts.append((x_R_end + tab_ext, tbot + tab_taper))
        pts.append((x_R_end, tbot))
    pts.append((x_R_end, y2 + c))
    
    # 7. Right Inner & Outer Side Bottom Edge
    pts.append((x_R_out2, y2))
    pts.append((L_bot, y2))
    
    # 8. Right Front Dust Flap
    pts.append((L_bot + FlapLength, y2 - 2 * t))
    pts.append((L_bot + FlapLength, y1 + 2 * t))
    pts.append((L_bot, y1))
    
    # 9. Front Panel Bottom Edge (with thumb cutout)
    R_thumb = min(15.0, L_bot / 10.0, H_in / 2.0)
    pts.append((L_bot / 2.0 + R_thumb, y1))
    for angle in range(0, 181, 15):
        rad = math.radians(angle)
        pts.append((L_bot / 2.0 + R_thumb * math.cos(rad), y1 + R_thumb * math.sin(rad)))
    pts.append((0, y1))
    
    # 10. Left Front Dust Flap
    pts.append((-FlapLength, y1 + 2 * t))
    pts.append((-FlapLength, y2 - 2 * t))
    pts.append((0, y2))
    
    # 11. Left Outer & Inner Side Bottom Edge
    pts.append((x_L_out2, y2))
    pts.append((x_L_end, y2 + c))
    
    # 12. Left Inner Side Left Edge (with 20% longer tabs)
    for (tbot, ttop) in tabs:
        tab_taper = min(t, (ttop - tbot) / 4.0)
        pts.append((x_L_end, tbot))
        pts.append((x_L_end - tab_ext, tbot + tab_taper))
        pts.append((x_L_end - tab_ext, ttop - tab_taper))
        pts.append((x_L_end, ttop))
    pts.append((x_L_end, y3 - c))
    
    # 13. Left Inner & Outer Side Top Edge
    pts.append((x_L_out2, y3))
    pts.append((0, y3))
    
    # 14. Left Back Dust Flap
    pts.append((-FlapLength, y3 + 2 * t))
    pts.append((-FlapLength, y4 - 2 * t))
    pts.append((0, y4))
    
    # 15. Left Back Panel Corner & Lid Left Edge
    pts.append((t, y4))
    pts.append((t, y5))
    
    # 16. Lid Tuck Flap Left Edge (with ear)
    pts.append((0.5 * t, y5 + 2 * t))
    pts.append((0.5 * t, y5 + ear_len))
    pts.append((2 * t, ear_taper_y))
    # Path closes back to pts[0] automatically
    
    # --- INTERNAL CUTS (SLOTS) ---
    cuts = []
    slot_w = max(2.0, t + 0.5)
    slot_c = 0.5 * t  # Slight overcut in Y to ensure easy tab insertion
    
    for (tbot, ttop) in tabs:
        # Right slot (Shifted INWARD so it sits strictly on the bottom panel)
        # x starts at L_bot - t - slot_w and ends at L_bot - t
        r_x_start = L_bot - t - slot_w
        r_x_end = L_bot - t
        cuts.append([
            (r_x_start, tbot - slot_c), (r_x_end, tbot - slot_c),
            (r_x_end, ttop + slot_c), (r_x_start, ttop + slot_c)
        ])
        
        # Left slot (Shifted INWARD so it sits strictly on the bottom panel)
        # x starts at t and ends at t + slot_w
        l_x_start = t
        l_x_end = t + slot_w
        cuts.append([
            (l_x_start, tbot - slot_c), (l_x_end, tbot - slot_c),
            (l_x_end, ttop + slot_c), (l_x_start, ttop + slot_c)
        ])

    # --- FOLD LINES (SCORES) ---
    folds = []
    
    # Main horizontal
    folds.append([(0, y2), (L_bot, y2)])         # Bottom to Front
    folds.append([(0, y3), (L_bot, y3)])         # Bottom to Back
    folds.append([(t, y4), (L_bot - t, y4)])     # Back to Lid
    folds.append([(t, y5), (L_bot - t, y5)])     # Lid to Tuck Flap
    
    # Dust Flap folds (Vertical)
    folds.append([(0, y1), (0, y2)])             # Left Front
    folds.append([(L_bot, y1), (L_bot, y2)])     # Right Front
    folds.append([(0, y3), (0, y4)])             # Left Back
    folds.append([(L_bot, y3), (L_bot, y4)])     # Right Back
    
    # Side panel rollover folds (Double scores for the fold-over gap)
    folds.append([(x_L_out1, y2), (x_L_out1, y3)])
    folds.append([(x_L_out2, y2), (x_L_out2, y3)])
    folds.append([(x_R_out1, y2), (x_R_out1, y3)])
    folds.append([(x_R_out2, y2), (x_R_out2, y3)])

    # Main vertical folds mapping Bottom to Sides
    # Because slots are now entirely on the bottom panel, these folds run clean corner to corner
    folds.append([(0, y2), (0, y3)])             # Left side to bottom
    folds.append([(L_bot, y2), (L_bot, y3)])     # Right side to bottom

    # --- SVG GENERATION & TRANSLATION ---
    all_x = [p[0] for p in pts]
    all_y = [p[1] for p in pts]
    for c_path in cuts:
        for p in c_path:
            all_x.append(p[0])
            all_y.append(p[1])
    
    min_x = min(all_x)
    min_y = min(all_y)
    max_x = max(all_x)
    max_y = max(all_y)

    margin = 10.0
    width_svg = max_x - min_x + 2 * margin
    height_svg = max_y - min_y + 2 * margin

    # Coordinate transform: shift to positive and invert Y-axis natively
    def tr(p):
        return (p[0] - min_x + margin, max_y - p[1] + margin)

    with open(filename, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_svg:.2f} {height_svg:.2f}" width="{width_svg:.2f}mm" height="{height_svg:.2f}mm">\n')
        
        # Styles: Cuts are red, Folds are blue and dashed
        f.write('<style>\n')
        f.write('  .cut { fill: none; stroke: red; stroke-width: 0.5; }\n')
        f.write('  .fold { fill: none; stroke: blue; stroke-width: 0.5; stroke-dasharray: 4,4; }\n')
        f.write('</style>\n')

        # Draw Perimeter Cut
        f.write('<path class="cut" d="M ')
        for i, p in enumerate(pts):
            tp = tr(p)
            f.write(f'{tp[0]:.2f},{tp[1]:.2f} ' if i == 0 else f'L {tp[0]:.2f},{tp[1]:.2f} ')
        f.write('Z" />\n')

        # Draw Slot Cuts
        for c_path in cuts:
            f.write('<path class="cut" d="M ')
            for i, p in enumerate(c_path):
                tp = tr(p)
                f.write(f'{tp[0]:.2f},{tp[1]:.2f} ' if i == 0 else f'L {tp[0]:.2f},{tp[1]:.2f} ')
            f.write('Z" />\n')

        # Draw Fold Lines
        for f_line in folds:
            tp0 = tr(f_line[0])
            tp1 = tr(f_line[1])
            f.write(f'<line class="fold" x1="{tp0[0]:.2f}" y1="{tp0[1]:.2f}" x2="{tp1[0]:.2f}" y2="{tp1[1]:.2f}" />\n')

        f.write('</svg>\n')
    
    print(f"Success! Saved precise inner-dimension FEFCO 0427 template to {filename}")
    print(f"Total layout dimensions: {width_svg:.2f}mm x {height_svg:.2f}mm")

#!/usr/bin/env python
import math
import sys
import argparse

# ... [The generate_fefco_0427_svg function remains the same as above] ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a CO2 laser cutter SVG for a FEFCO 0427 cardboard box.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--length", type=float, help="Inside length (mm)")
    parser.add_argument("--width", type=float, help="Inside width/depth (mm)")
    parser.add_argument("--height", type=float, help="Inside height (mm)")
    parser.add_argument("--thickness", type=float, help="Cardboard thickness (mm)")
    parser.add_argument("--output", type=str, help="Output SVG filename (default: box.svg)", default="box_FEFCO0427.svg")
    
    # If no arguments are passed, print help and exit
    if len(sys.argv) == 1:
        print("\n--- FEFCO 0427 SVG Generator ---")
        print("No parameters provided.")
        print("\nUsage example:")
        print("  python wkbox.py --length 200 --width 200 --height 30 --thickness 2.5 --output box.svg")
        print("\nRequired arguments:")
        print("  --length     : internal length of the box.")
        print("  --width      : internal width  of the box.")
        print("  --height     : internal height of the box.")
        print("  --thickness  : thickness of the material.")
        print("\nOptional:")
        print("  --output     : filename (default = box_FEFCO0427.svg).")
        sys.exit(1)

    args = parser.parse_args()
    
    # Check if required dimensions are missing (since default is None)
    required = [args.length, args.width, args.height, args.thickness]
    if any(v is None for v in required):
        print("Error: Please provide all dimensions: --length, --width, --height, and --thickness.")
        sys.exit(1)

    generate_fefco_0427_svg(
        length_in=args.length,
        width_in=args.width,
        height_in=args.height,
        thickness=args.thickness,
        filename=args.output
    )