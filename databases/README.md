# databases/

Drop your `.TDB` files here and the server finds them with no
configuration; this directory is the second thing it looks at, after
`OC_DB_DIR`.

Nothing is committed here. The databases this project was developed
against ship with OpenCalphad or carry their own licences -- `iron4cd.TDB`
is CC BY, others come with the distribution -- and redistributing them
from this repository would mean asserting terms for files whose terms were
not checked one by one.

`.gitignore` keeps `*.TDB` out of the repository but keeps this file, so
the directory exists in a fresh clone and the instruction is here rather
than only in the top-level README.
