""" WTF form setup for images """
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (SubmitField, TextAreaField,
                     FloatField, SelectField)
from wtforms.validators import DataRequired


class ImageDetailsForm(FlaskForm):
    latitude = FloatField('Latitude', validators= [DataRequired()],
                          render_kw={"aria-label": "Latitude"})
    longitude = FloatField('Longitude', validators= [DataRequired()],
                           render_kw={"aria-label": "Longitude"})
    notes = TextAreaField('Additional notes')
    submit = SubmitField('Submit')


class ImageDetailsNotesForm(FlaskForm):
    notes = TextAreaField('Additional notes')
    submit = SubmitField('Submit')


class ImageUploadForm(FlaskForm):
    image = FileField("Upload an Image",
                      validators=[FileRequired(),
                                  FileAllowed(["jpg", "jpeg", "png", "tiff"],
                                              "Images only!")])
    assay = SelectField("Select Assay", choices=[])
    submit = SubmitField("Submit")
