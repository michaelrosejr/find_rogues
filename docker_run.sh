docker run -it \
    -v ./.env.yaml:/.env.yaml \
    -v ./temp:/app/temp \
    find_rogues $1
