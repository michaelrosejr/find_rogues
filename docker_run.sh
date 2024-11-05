docker run -it \
    -v ./.env.yaml:/app/.env.yaml \
    -v ./temp:/app/temp \
    find_rogues $1
