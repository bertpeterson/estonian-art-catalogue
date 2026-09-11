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
# Ask the domain's own nameservers, which hold the zone, rather than a resolver that
# holds a copy of it. A cache answers with whatever it was told up to half an hour ago:
# before the records existed it insists the name does not exist, and after a record is
# deleted it keeps serving it until the TTL runs out -- and the public resolvers are
# many independent caches, so they disagree with each other meanwhile. The zone is the
# only answer that is true now; caches converge on it within the TTL either way.
AUTH=$(dig +short "$DOMAIN" NS 2>/dev/null | head -1)
[ -n "$AUTH" ] || AUTH=$(dig +short @8.8.8.8 "$DOMAIN" NS 2>/dev/null | head -1)
[ -n "$AUTH" ] || { echo "  ✗ ${DOMAIN} has no nameservers — the domain is registered but not delegated."; exit 1; }
echo "  asking ${AUTH%.}"
GOT=$(dig +short "@${AUTH%.}" "$DOMAIN" A 2>/dev/null | tr '\n' ' ')
[ -n "$GOT" ] || { echo "  ✗ ${DOMAIN} has no A records yet — configure DNS first, then re-run."; exit 1; }
# Every address must be GitHub's, not merely one of them. A registrar that parks the
# domain on its own server leaves that record behind when you add the Pages ones, and
# five A records means browsers round-robin: roughly one visitor in five lands on the
# parking page, and GitHub may refuse to issue the certificate. Ask for the exact set.
STRAY=""; for ip in $GOT; do case " $GH_IPS " in *" $ip "*) ;; *) STRAY="$STRAY $ip";; esac; done
[ -z "$STRAY" ] || { echo "  ✗ resolves to addresses that are not GitHub Pages:$STRAY"
                     echo "    delete those A records, keep only: $GH_IPS"; exit 1; }
for ip in $GH_IPS; do case " $GOT " in *" $ip "*) ;; *) echo "  ✗ missing A record $ip"; exit 1;; esac; done
echo "  ✓ resolves to GitHub Pages, and to nothing else"

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
