FROM python:3
COPY vns.py problem.py optsolution.py flask_app.py requirements.txt ./
RUN pip install -r requirements.txt
EXPOSE 8080
CMD python flask_app.py