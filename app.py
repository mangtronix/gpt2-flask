from flask import Flask, render_template, request, flash, redirect, url_for
import yaml
from config import Config
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
from web_model_generator import init_model, generate_response
import gpt_mysql_connector


DEBUG = True
NGROK = True


app = Flask(__name__)

if NGROK:
   # We'll run the server with ngrok tunneling
   from flask_ngrok import run_with_ngrok
   run_with_ngrok(app)

app.config.from_object(Config)

sess, context, saver, output, enc = init_model()


class ReusableForm(Form):
    prompt = TextAreaField('', validators=[validators.required()])

    @app.route("/", methods=['GET', 'POST'])
    def hello():
        form = ReusableForm(request.form)
        result_text = ''
        prompt = ''
        new_prompt = ''
        if request.method == 'POST':
            prompt = request.form['prompt']

            if form.validate():
                result_text = generate_response(prompt, sess, context, saver, enc, output)

                # Use the last characters of the result (GPT output) for the new prompt
                # inside the entry form
                continuation_characters = 100
                new_prompt = result_text[-continuation_characters:]
                print("New prompt: %s" % new_prompt)
                form['prompt'] = new_prompt

                if gpt_mysql_connector.is_connected():
                    guid, still_available = gpt_mysql_connector.insert_gpt_prompt(prompt, result_text)
                    if still_available:
                        return redirect(url_for('load_guid', guid=guid))
                    else:
                        return render_template('index.html', form=form, prompt_text = new_prompt, old_prompt_text=prompt, result_text=result_text)
                else:
                    return render_template('index.html', form=form, prompt_text = new_prompt, old_prompt_text=prompt, result_text=result_text)
            else:
                flash('All Fields Are Required')

        return render_template('index.html', form=form, prompt_text=prompt, result_text=result_text)

    @app.route('/a/<guid>', methods = ['GET'])
    def load_guid(guid):
        form = ReusableForm(request.form)
        if gpt_mysql_connector.is_connected():
            saved_prompt, response, still_available = (gpt_mysql_connector.get_gpt_prompt(guid))
            return render_template('index.html', form=form, prompt_text=saved_prompt, result_text=response)
            if not still_available:
                db_available = False
        else:
            return render_template('index.html', form=form, prompt_text='Database Failure', result_text='Database Unavailable, Cannot Retrieve Saved Results')


if __name__ == "__main__":
    app.run()
