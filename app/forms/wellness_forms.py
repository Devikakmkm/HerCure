from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectMultipleField, SubmitField, widgets
from wtforms.validators import DataRequired, NumberRange

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class WellnessQuizForm(FlaskForm):
    age = IntegerField('Age', 
        validators=[DataRequired(), NumberRange(min=12, max=100, message="Please enter a valid age.")],
        render_kw={"placeholder": "e.g., 28"}
    )
    cycle_length = IntegerField('Average Cycle Length (days)', 
        validators=[DataRequired(), NumberRange(min=15, max=90, message="Please enter a realistic cycle length.")],
        render_kw={"placeholder": "e.g., 28"}
    )
    period_length = IntegerField('Average Period Length (days)', 
        validators=[DataRequired(), NumberRange(min=1, max=15, message="Please enter a realistic period length.")],
        render_kw={"placeholder": "e.g., 5"}
    )
    symptoms = MultiCheckboxField('What symptoms are you currently experiencing?', 
        choices=[
            ('cramps', 'Cramps'),
            ('bloating', 'Bloating'),
            ('fatigue', 'Fatigue'),
            ('headache', 'Headache'),
            ('acne', 'Acne'),
            ('mood_swings', 'Mood Swings'),
            ('breast_tenderness', 'Breast Tenderness'),
            ('nausea', 'Nausea')
        ],
        validators=[DataRequired(message="Please select at least one symptom.")]
    )
    submit = SubmitField('Get My Wellness Plan')
