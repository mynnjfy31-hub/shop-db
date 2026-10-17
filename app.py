from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello Moein! Flask is working!"
@app.route('/about')
def about():
    return "This is Moein`s first Flask project!"
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

    