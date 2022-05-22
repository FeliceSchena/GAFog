FROM python:3
COPY vns.py problem.py optsolution.py flask.py ./
RUN pip install flask deap requests
EXPOSE 8080
CMD python flask_app.py