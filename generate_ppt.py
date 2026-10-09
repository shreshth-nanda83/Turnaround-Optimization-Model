from pptx import Presentation

def create_presentation():
    prs = Presentation()
    
    # Slide 1: Title Slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "Commercial Fleet Operations &\nTurnaround Optimization Model"
    subtitle.text = "End-to-End Workflow & Architecture\nPredicting Cascading Delays to Save Operational Costs"

    # Slide 2: Business Problem
    bullet_slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(bullet_slide_layout)
    title_shape = slide.shapes.title
    body_shape = slide.placeholders[1]
    
    title_shape.text = "The Business Problem: Cascading Delays"
    tf = body_shape.text_frame
    tf.text = "Airlines operate on incredibly tight turnaround schedules."
    
    p = tf.add_paragraph()
    p.text = "The Turnaround Buffer: The scheduled ground time between arrival and departure."
    p.level = 1
    
    p = tf.add_paragraph()
    p.text = "The Problem: When an aircraft arrives late, the buffer is breached."
    p.level = 1
    
    p = tf.add_paragraph()
    p.text = "The Impact: One delay propagates to the next flight (cascading delays)."
    p.level = 1
    
    p = tf.add_paragraph()
    p.text = "The Cost: The FAA estimates each minute of delay costs airlines ~$75."
    p.level = 1

    # Slide 3: The Architecture Workflow
    slide = prs.slides.add_slide(bullet_slide_layout)
    title_shape = slide.shapes.title
    body_shape = slide.placeholders[1]
    
    title_shape.text = "Project Workflow Architecture"
    tf = body_shape.text_frame
    tf.text = "How the pipeline operates:"
    
    p = tf.add_paragraph()
    p.text = "1. Data Ingestion (db_setup.py)"
    p.level = 1
    p2 = tf.add_paragraph()
    p2.text = "Reads raw CSV, formats timestamps, cleans data, loads into SQLite."
    p2.level = 2

    p = tf.add_paragraph()
    p.text = "2. Analytical Engine (turnaround_analytics.sql)"
    p.level = 1
    p2 = tf.add_paragraph()
    p2.text = "Uses Window Functions to track aircraft across flights and calculate ground turnaround."
    p2.level = 2

    p = tf.add_paragraph()
    p.text = "3. Predictive Modeling (train_model.py)"
    p.level = 1
    p2 = tf.add_paragraph()
    p2.text = "Trains a Random Forest classifier using engineered features to predict buffer breaches."
    p2.level = 2

    # Slide 4: How to Run the Project
    slide = prs.slides.add_slide(bullet_slide_layout)
    title_shape = slide.shapes.title
    body_shape = slide.placeholders[1]
    
    title_shape.text = "How to Run the Pipeline"
    tf = body_shape.text_frame
    tf.text = "Step-by-step execution:"
    
    p = tf.add_paragraph()
    p.text = "Step 1: Install dependencies (pip install -r requirements.txt)"
    p.level = 1

    p = tf.add_paragraph()
    p.text = "Step 2: Build the Database (python src/db_setup.py)"
    p.level = 1

    p = tf.add_paragraph()
    p.text = "Step 3: Run the SQL Analytics (sqlite3 operations.db < sql/turnaround_analytics.sql)"
    p.level = 1

    p = tf.add_paragraph()
    p.text = "Step 4: Run the ML Model (python src/train_model.py)"
    p.level = 1

    # Slide 5: Results & Impact
    slide = prs.slides.add_slide(bullet_slide_layout)
    title_shape = slide.shapes.title
    body_shape = slide.placeholders[1]
    
    title_shape.text = "Model Results & Financial Impact"
    tf = body_shape.text_frame
    tf.text = "Performance Benchmarks:"
    
    p = tf.add_paragraph()
    p.text = "Precision (78.4%): High accuracy when flagging a delay."
    p.level = 1
    
    p = tf.add_paragraph()
    p.text = "Recall (65.9%): Successfully anticipated 66% of actual delays."
    p.level = 1
    
    p = tf.add_paragraph()
    p.text = "Predicted Delay Cost Exposure: $51,204,225"
    p.level = 1
    
    p = tf.add_paragraph()
    p.text = "Potential Operational Savings: $10,240,845 (assuming 20% mitigation)"
    p.level = 1

    prs.save('Workflow_Presentation.pptx')
    print("Presentation generated successfully!")

if __name__ == '__main__':
    create_presentation()
