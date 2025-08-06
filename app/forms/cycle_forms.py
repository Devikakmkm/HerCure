from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SelectMultipleField, TextAreaField, SubmitField, BooleanField, DateField, IntegerField, FieldList, FormField, HiddenField, RadioField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from flask_wtf.file import FileField, FileAllowed

class CycleLogForm(FlaskForm):
    """Form for logging cycle data"""
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[Optional()])
    flow_intensity = RadioField('Flow Intensity', 
                               choices=[
                                   ('light', 'Light'),
                                   ('moderate', 'Moderate'),
                                   ('heavy', 'Heavy')
                               ], 
                               validators=[DataRequired()],
                               default='moderate')
    pain_level = RadioField('Pain Level', 
                           choices=[
                               ('none', 'None'),
                               ('mild', 'Mild'),
                               ('moderate', 'Moderate'),
                               ('severe', 'Severe')
                           ], 
                           validators=[DataRequired()],
                           default='none')
    mood = RadioField('Mood', 
                      choices=[
                          ('happy', 'Happy'),
                          ('normal', 'Normal'),
                          ('sad', 'Sad'),
                          ('irritable', 'Irritable'),
                          ('anxious', 'Anxious')
                      ],
                      validators=[DataRequired()],
                      default='normal')
    symptoms = SelectMultipleField('Symptoms', 
                               choices=[
                                   ('cramps', 'Cramps'),
                                   ('headache', 'Headache'),
                                   ('bloating', 'Bloating'),
                                   ('tender_breasts', 'Tender Breasts'),
                                   ('backache', 'Backache'),
                                   ('acne', 'Acne'),
                                   ('fatigue', 'Fatigue')
                               ],
                               validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Entry')

    def __init__(self, *args, **kwargs):
        super(CycleLogForm, self).__init__(*args, **kwargs)
        # Set default date to today if not provided
        if not self.start_date.data:
            from datetime import date
            self.start_date.data = date.today()
