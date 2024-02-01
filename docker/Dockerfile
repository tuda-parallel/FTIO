FROM python:latest

COPY ../ftio /freq_io/ftio
# COPY ioparse /freq_io/ioparse
# COPY install /freq_io/install
# COPY prediction /freq_io/prediction
# COPY predictor.py /freq_io/
# COPY ftio.py /freq_io/

WORKDIR /freq_io

# RUN  python3 -m venv ./venv
RUN ls
RUN  python3 -m pip install .  
    
CMD ["ftio.py", "-e", "no"]