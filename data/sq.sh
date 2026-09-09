#!/bin/bash
# sq.sh <file.rq> <out.json>
curl -s -m 180 -H 'Accept: application/sparql-results+json' \
  -H 'User-Agent: EstonianArtRegister/1.0 (offline research compile)' \
  --data-urlencode "query@$1" https://query.wikidata.org/sparql > "$2"
