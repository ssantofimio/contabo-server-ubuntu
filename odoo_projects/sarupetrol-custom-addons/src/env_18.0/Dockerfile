# <OOW> : Copy of https://github.com/odoo/odoo/blob/18.0/setup/package.dfsrc
FROM debian:bookworm

RUN apt-get update && \
    apt-get install -y locales && \
    rm -rf /var/lib/apt/lists/*

# Reconfigure locales such that postgresql uses UTF-8 encoding
RUN dpkg-reconfigure locales && \
    locale-gen C.UTF-8 && \
    /usr/sbin/update-locale LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apt-get update -qq &&  \
    apt-get upgrade -qq -y && \
    apt-get install \
        postgresql \
        postgresql-server-dev-all \
        postgresql-client \
        adduser \
        libldap2-dev \
        libsasl2-dev \
        python3-pip \
        python3-venv \
        python3-wheel \
        build-essential \
        python3 -y && \
    rm -rf /var/lib/apt/lists/*

# <OOW> Install Debian packages
COPY extra_debian_requirements.txt /extra_debian_requirements.txt
COPY addons_debian_requirements.txt /addons_debian_requirements.txt
RUN apt-get update -qq \
    && apt-get install -y git \
    && grep -vE '^\s*#|^\s*$' extra_debian_requirements.txt | xargs apt-get install -y --no-install-recommends \
    && grep -vE '^\s*#|^\s*$' addons_debian_requirements.txt | xargs apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# <OOW> Install Python librairies
COPY ./src/odoo/requirements.txt /odoo_python_requirements.txt
COPY addons_python_requirements.txt /addons_python_requirements.txt
COPY extra_python_requirements.txt /extra_python_requirements.txt
RUN pip3 install --upgrade pip --break-system-packages \
    && python3 -m pip install --no-cache-dir setuptools-scm --break-system-packages \
    && python3 -m pip install --no-cache-dir -r /odoo_python_requirements.txt --break-system-packages \
    && python3 -m pip install --no-cache-dir -r /extra_python_requirements.txt --break-system-packages \
    && python3 -m pip install --no-cache-dir -r /addons_python_requirements.txt --break-system-packages

# <OOW> Get local user id and set it to the odoo user
ARG LOCAL_USER_ID

RUN useradd --uid $LOCAL_USER_ID --non-unique odoo

USER odoo
