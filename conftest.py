# Present so pytest puts the repo root on sys.path -- `common` is a plain
# directory, not an installed package, and the product scripts each do their
# own sys.path.insert (e.g. products/ipad/vinted.py:10) which pytest does not do.
