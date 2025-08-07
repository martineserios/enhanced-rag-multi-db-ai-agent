FROM python:3.11-slim-buster

WORKDIR /app

ARG INSTALL_UV=false

# Install uv if argument is true
RUN if [ "$INSTALL_UV" = "true" ] ; then \
    pip install uv && \
    echo "uv installed"; \
    else \
    echo "uv not installed"; \
    fi

COPY pyproject.toml uv.lock /app/

COPY . /app

# Install dependencies using uv if installed, otherwise use pip
RUN if [ "$INSTALL_UV" = "true" ] ; then \
    uv sync; \
    else \
    pip install --no-cache-dir -r requirements.txt; \
    fi

EXPOSE 8000

ENV PATH="/root/.local/bin:${PATH}"

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]