FROM python:3
COPY ga.py ../FogProbem/*.py fogindividual.py flask_app.py ./
RUN pip install flask deap requests numpy
EXPOSE 8080
CMD python flask_app.py