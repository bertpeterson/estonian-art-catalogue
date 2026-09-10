#!/usr/bin/env bash
# Move the catalogue to a custom domain. Run ONLY after DNS resolves — see below.
#
#   ./switch-domain.sh estonianartcatalogue.com
#
# GitHub Pages serves the site at whatever CNAME says, so committing that file before
# DNS is live takes the site offline at both addresses. This script checks first.
set -euo pipefail
DOMAIN="${1:?usage: ./switch-domain.sh example.com}"
OLD="https://bertpeterson.github.io/estonian-art-catalogue"
NEW="https://${DOMAIN}"

echo "checking DNS for ${DOMAIN}…"
GH_IPS="185.199.108.153 185.199.109.153 185.199.110.153 185.199.111.153"
GOT=$(dig +short "$DOMAIN" A | tr '\n' ' ')
[ -n "$GOT" ] || { echo "  ✗ ${DOMAIN} does not resolve yet — configure DNS first, then re-run."; exit 1; }
MATCH=0; for ip in $GOT; do case " $GH_IPS " in *" $ip "*) MATCH=1;; esac; done
[ "$MATCH" = 1 ] || { echo "  ✗ resolves to: $GOT"; echo "    expected GitHub Pages: $GH_IPS"; exit 1; }
echo "  ✓ resolves to GitHub Pages"

echo "$DOMAIN" > static/CNAME                      # copied into site/ by build_site.py
sed -i '' "s#^BASE = \".*\"#BASE = \"${NEW}\"#" build_pages.py
sed -i '' "s#${OLD}/#${NEW}/#g; s#${OLD}#${NEW}#g" tpl_head.html README.md build_artifact.py
./build_site.sh >/dev/null
echo
echo "switched to ${NEW}"
echo "  static/CNAME written, BASE and canonical/OpenGraph URLs updated, site rebuilt"
echo
echo "next:"
echo "  git add -A && git commit -m 'Move to ${DOMAIN}' && git push"
echo "  then in the repo: Settings > Pages > Custom domain = ${DOMAIN}, tick Enforce HTTPS"
echo "  and add ${NEW}/ as a new property in Search Console"
