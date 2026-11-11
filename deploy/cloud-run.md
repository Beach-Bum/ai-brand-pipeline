# Deploying the MCP server to Cloud Run

NOT DONE YET. These are the steps as planned; none has been run. Needs a Google Cloud project with
billing on and the `gcloud` command installed.

```bash
gcloud auth login
gcloud config set project <project-id>
gcloud run deploy brand-agent \
  --source . --dockerfile deploy/Dockerfile \
  --region europe-west4 \
  --set-env-vars BRAND_ID=<id> \
  --no-allow-unauthenticated
```

## To check on the first deploy

1. **Host check.** Over HTTP the server answered `initialize` on 127.0.0.1. The MCP library has a
   transport security setting that can refuse requests whose Host header it does not expect; a
   request through Cloud Run's address may need that setting changed in `server.py`.
2. **Access.** `--no-allow-unauthenticated` keeps the service private. Decide who may call it
   before opening it: the tools only read a brand pack, but an open endpoint is still an open endpoint.
3. **Sessions.** Cloud Run can run several copies. If a client loses its session between calls,
   start the server with `stateless_http=True`.
4. **Flags.** Confirm the `gcloud run deploy` flags above against the current documentation.
