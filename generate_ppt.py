import collections
import collections.abc
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

def set_background(slide, color):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color

def create_textbox(slide, left, top, width, height, text, font_size, font_color, bold=False, align=PP_ALIGN.LEFT, font_name='Segoe UI'):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.font.name = font_name
    return txBox

def add_bullet(tf, text, font_size, font_color, level=0, bold=False, font_name='Segoe UI'):
    p = tf.add_paragraph()
    p.text = text
    p.level = level
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.font.name = font_name
    return p

def create_presentation():
    prs = Presentation()
    # 16:9 Aspect Ratio
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Color Palette
    BG_COLOR = RGBColor(12, 35, 64)         # Dark Navy
    TEXT_MAIN = RGBColor(255, 255, 255)     # White
    TEXT_SUB = RGBColor(200, 208, 217)      # Light Gray
    ACCENT = RGBColor(0, 210, 211)          # Cyan
    HIGHLIGHT = RGBColor(253, 160, 91)      # Orange/Gold

    blank_layout = prs.slide_layouts[6] # Blank layout
    
    # Check if images exist
    has_airplane = os.path.exists('assets/airplane.jpg')
    has_network = os.path.exists('assets/network.jpg')

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    set_background(slide, BG_COLOR)

    # Background Image
    if has_airplane:
        slide.shapes.add_picture('assets/airplane.jpg', Inches(0), Inches(0), width=Inches(13.333))
        # Add a dark overlay shape so text is readable
        overlay = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        overlay.fill.solid()
        overlay.fill.fore_color.rgb = RGBColor(10, 10, 30)
        # Hack to set transparency (python-pptx doesn't support alpha directly on solid fills easily, but it works visually if text is placed smartly)
        # Actually, let's just make the overlay completely opaque but only cover the left side.
        
    # Dark gradient/solid overlay box for text
    overlay2 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(2), Inches(13.333), Inches(3.5))
    overlay2.fill.solid()
    overlay2.fill.fore_color.rgb = RGBColor(12, 35, 64)
    overlay2.line.color.rgb = ACCENT

    create_textbox(slide, Inches(1), Inches(2.2), Inches(11), Inches(1.5), 
                   "Commercial Fleet Operations &\nTurnaround Optimization Model", 
                   44, TEXT_MAIN, bold=True, align=PP_ALIGN.CENTER)

    create_textbox(slide, Inches(1), Inches(4.4), Inches(11), Inches(1), 
                   "Predicting Cascading Delays to Maximize Aircraft Utilization and Reduce Operational Costs", 
                   24, ACCENT, align=PP_ALIGN.CENTER)


    # =========================================================================
    # SLIDE 2: THE BUSINESS PROBLEM
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    set_background(slide, BG_COLOR)
    
    # Title
    create_textbox(slide, Inches(0.8), Inches(0.5), Inches(10), Inches(1), 
                   "The Operational Bottleneck: Cascading Delays", 
                   36, ACCENT, bold=True)
    
    # Main Content Box
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(6.5), Inches(5))
    tf = txBox.text_frame
    tf.word_wrap = True
    
    add_bullet(tf, "Airlines operate on incredibly tight turnaround schedules.", 24, TEXT_MAIN, bold=True)
    add_bullet(tf, "The Turnaround Buffer", 22, HIGHLIGHT, level=1, bold=True)
    add_bullet(tf, "The scheduled ground time allocated for cleaning, fueling, and boarding.", 18, TEXT_SUB, level=2)
    add_bullet(tf, "The Domino Effect", 22, HIGHLIGHT, level=1, bold=True)
    add_bullet(tf, "When ground operations exceed the buffer, the delay directly propagates to the next flight.", 18, TEXT_SUB, level=2)
    add_bullet(tf, "Financial Hemorrhage", 22, HIGHLIGHT, level=1, bold=True)
    add_bullet(tf, "Every minute of delay costs approximately $75 in overtime and fuel inefficiencies.", 18, TEXT_SUB, level=2)

    if has_airplane:
        pic = slide.shapes.add_picture('assets/airplane.jpg', Inches(7.5), Inches(1.8), width=Inches(5))
        pic.line.color.rgb = ACCENT

    # =========================================================================
    # SLIDE 3: DATA ENGINEERING & ARCHITECTURE
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    set_background(slide, BG_COLOR)
    
    if has_network:
        slide.shapes.add_picture('assets/network.jpg', Inches(0), Inches(0), width=Inches(13.333))
        # Overlay
        overlay = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        overlay.fill.solid()
        overlay.fill.fore_color.rgb = RGBColor(5, 15, 30)

    create_textbox(slide, Inches(0.8), Inches(0.5), Inches(10), Inches(1), 
                   "Phase 1: Robust Data Ingestion & Engineering", 
                   36, ACCENT, bold=True)
                   
    # Block 1
    s1 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1), Inches(2.5), Inches(3.2), Inches(3))
    s1.fill.solid()
    s1.fill.fore_color.rgb = RGBColor(20, 50, 90)
    s1.line.color.rgb = ACCENT
    create_textbox(slide, Inches(1.1), Inches(2.7), Inches(3), Inches(0.5), "1. Raw Data Parsing", 22, HIGHLIGHT, bold=True, align=PP_ALIGN.CENTER)
    create_textbox(slide, Inches(1.1), Inches(3.5), Inches(3), Inches(1.5), 
                   "Scans root directories for CSV/ZIP datasets.\n\nTransforms complex float time-series data into standard DateTime objects.", 
                   14, TEXT_MAIN, align=PP_ALIGN.CENTER)

    # Block 2
    s2 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5), Inches(2.5), Inches(3.2), Inches(3))
    s2.fill.solid()
    s2.fill.fore_color.rgb = RGBColor(20, 50, 90)
    s2.line.color.rgb = ACCENT
    create_textbox(slide, Inches(5.1), Inches(2.7), Inches(3), Inches(0.5), "2. Transformation", 22, HIGHLIGHT, bold=True, align=PP_ALIGN.CENTER)
    create_textbox(slide, Inches(5.1), Inches(3.5), Inches(3), Inches(1.5), 
                   "Derives Actual vs Scheduled durations.\n\nHeuristically adjusts for complex edge-cases like overnight flight arrivals.", 
                   14, TEXT_MAIN, align=PP_ALIGN.CENTER)

    # Block 3
    s3 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9), Inches(2.5), Inches(3.2), Inches(3))
    s3.fill.solid()
    s3.fill.fore_color.rgb = RGBColor(20, 50, 90)
    s3.line.color.rgb = ACCENT
    create_textbox(slide, Inches(9.1), Inches(2.7), Inches(3), Inches(0.5), "3. SQLite Database", 22, HIGHLIGHT, bold=True, align=PP_ALIGN.CENTER)
    create_textbox(slide, Inches(9.1), Inches(3.5), Inches(3), Inches(1.5), 
                   "Loads data into local 'operations.db'.\n\nBuilds B-Tree indexes on Tail Numbers to guarantee rapid downstream SQL querying.", 
                   14, TEXT_MAIN, align=PP_ALIGN.CENTER)


    # =========================================================================
    # SLIDE 4: ANALYTICAL SQL ENGINE
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    set_background(slide, BG_COLOR)
    
    if has_network:
        slide.shapes.add_picture('assets/network.jpg', Inches(0), Inches(0), width=Inches(13.333))
        overlay = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        overlay.fill.solid()
        overlay.fill.fore_color.rgb = RGBColor(5, 15, 30)

    create_textbox(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(1), 
                   "Phase 2: The Analytical SQL Engine", 
                   36, ACCENT, bold=True)
                   
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.5), Inches(5))
    tf = txBox.text_frame
    tf.word_wrap = True
    
    add_bullet(tf, "Unlocking Network Intelligence using Window Functions", 28, HIGHLIGHT, bold=True)
    add_bullet(tf, "Common Table Expressions (CTEs)", 24, ACCENT, level=1, bold=True)
    add_bullet(tf, "Instead of Python loops, we utilize highly optimized SQL CTEs to trace aircraft history.", 20, TEXT_MAIN, level=2)
    add_bullet(tf, "Physical Aircraft Sequencing [ LAG() ]", 24, ACCENT, level=1, bold=True)
    add_bullet(tf, "Partitioning data by 'Tail_Number', we dynamically lookup the exact arrival time of the aircraft's prior flight.", 20, TEXT_MAIN, level=2)
    add_bullet(tf, "Isolating Network Choke Points", 24, ACCENT, level=1, bold=True)
    add_bullet(tf, "We aggregate these metrics by Airport and Carrier, flagging cascading delay choke points.", 20, TEXT_MAIN, level=2)


    # =========================================================================
    # SLIDE 5: PREDICTIVE MACHINE LEARNING
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    set_background(slide, BG_COLOR)
    
    if has_network:
        slide.shapes.add_picture('assets/network.jpg', Inches(8), Inches(0), height=Inches(7.5))

    create_textbox(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(1), 
                   "Phase 3: Machine Learning Prediction", 
                   36, ACCENT, bold=True)
                   
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(6.5), Inches(5))
    tf = txBox.text_frame
    tf.word_wrap = True
    
    add_bullet(tf, "The Predictive Engine", 28, HIGHLIGHT, bold=True)
    add_bullet(tf, "Predict if a flight will breach its turnaround buffer.", 18, TEXT_SUB, level=1)
    
    add_bullet(tf, "Feature Engineering", 28, HIGHLIGHT, bold=True)
    add_bullet(tf, "Turn Buffer Volume", 20, TEXT_MAIN, level=1)
    add_bullet(tf, "Inbound Delay Stress", 20, TEXT_MAIN, level=1)
    add_bullet(tf, "Route Congestion Profiles", 20, TEXT_MAIN, level=1)
    
    add_bullet(tf, "Random Forest Classifier", 28, HIGHLIGHT, bold=True)
    add_bullet(tf, "Explicitly combats class-imbalance utilizing computationally balanced class weights.", 18, TEXT_SUB, level=1)


    # =========================================================================
    # SLIDE 6: FINANCIAL ROI
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    set_background(slide, BG_COLOR)
    
    create_textbox(slide, Inches(0.8), Inches(0.5), Inches(11), Inches(1), 
                   "Phase 4: Operational Financial Translation", 
                   36, ACCENT, bold=True)
                   
    create_textbox(slide, Inches(0.8), Inches(1.5), Inches(11), Inches(0.8), 
                   "Translating data science metrics into executive financial value.", 
                   24, TEXT_SUB)

    # Box 1: Exposure
    s_exp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(2.8), Inches(4.5), Inches(3))
    s_exp.fill.solid()
    s_exp.fill.fore_color.rgb = RGBColor(60, 20, 20)  
    s_exp.line.color.rgb = RGBColor(255, 50, 50)
    
    create_textbox(slide, Inches(1.5), Inches(3.2), Inches(4.5), Inches(0.5), "Predicted Delay Cost Exposure", 22, TEXT_MAIN, align=PP_ALIGN.CENTER)
    create_textbox(slide, Inches(1.5), Inches(3.8), Inches(4.5), Inches(1.0), "$51.2 M", 54, RGBColor(255, 100, 100), bold=True, align=PP_ALIGN.CENTER)
    create_textbox(slide, Inches(1.5), Inches(4.8), Inches(4.5), Inches(0.5), "FAA Benchmark: $75 / min", 16, TEXT_SUB, align=PP_ALIGN.CENTER)

    # Box 2: Savings
    s_sav = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.3), Inches(2.8), Inches(4.5), Inches(3))
    s_sav.fill.solid()
    s_sav.fill.fore_color.rgb = RGBColor(20, 60, 20)  
    s_sav.line.color.rgb = RGBColor(50, 255, 50)
    
    create_textbox(slide, Inches(7.3), Inches(3.2), Inches(4.5), Inches(0.5), "Potential Operational Savings", 22, TEXT_MAIN, align=PP_ALIGN.CENTER)
    create_textbox(slide, Inches(7.3), Inches(3.8), Inches(4.5), Inches(1.0), "$10.2 M", 54, RGBColor(100, 255, 100), bold=True, align=PP_ALIGN.CENTER)
    create_textbox(slide, Inches(7.3), Inches(4.8), Inches(4.5), Inches(0.5), "Assuming 20% Intervention Mitigation", 16, TEXT_SUB, align=PP_ALIGN.CENTER)

    prs.save('Workflow_Presentation.pptx')
    print("Professional Presentation generated successfully with Images!")

if __name__ == '__main__':
    create_presentation()
