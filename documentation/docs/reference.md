# The Rattlesnake Documentation was made with MkDocs

For full documentation visit [mkdocs.org](https://www.mkdocs.org).

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs -h` - Print help message and exit.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.

## LaTeX

Install the plugin using `pip`:

```sh
pip install mkdocs-with-katex
```

Update the `mkdocs.yml` to include:

```yaml
plugins:
  - with-katex
```

Include equations, such as inline equations $F = ma$ and block equations:

$$ \frac{1}{\pi} = \sum_{n=0}^{\infty} \frac{(4n)!}{(n!)^4} \frac{26390n+1103}{396^{4n}} $$
