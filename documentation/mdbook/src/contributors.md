## Contributors

* Daniel P. Rohe
* Ryan Schultz
* Norman Hunter


### Development

#### Documentation

Update the
[online documentation](https://sandialabs.github.io/rattlesnake-vibration-controller/book/)
as follows:

```sh
# change to the project directory
cd rattlesnake/rattlesnake-vibration-controller

# activate the virtual environment
source .venv/bin/activate       # for bash shell
source .venv/bin/activate.csh   # for c shell
source .venv/bin/activate.fish  # for fish shell
.\.venv\Scripts\activate        # for powershell

# change to the mdbook directory
cd rattlesnake/rattlesnake-vibration-controller/documentation/mdbook

# update the source markdown (.md) files as necessary in the
# rattlesnake/rattlesnake-vibration-controller/documentation/mdbook/src
# folder

# build the mdbook build, which build the target to the
# rattlesnake/rattlesnake-vibration-controller/documentation/mdbook/book
# folder
mdbook build

# visualize the mdbook in a local web browser
mdbook serve --open
```

##### Bibliography

To create the bibliography, use [`mdbook-bib`](https://crates.io/crates/mdbook-bib), a popular and well-documented third-party plugin.

[Cargo](https://rust-lang.org/tools/install/),
the Rust programming language's package manager, is a prerequisite to get the plugin.

1. Install the plugin via Cargo:

```sh
cargo install mdbook-bib
```

2. Prepare your bibliography file:

The `mdbook-bib` plugin uses the standard BibLaTeX (`.bib`) format for references.
Create a `.bib` file (e.g., `bibliography.bib`) in the root of the `documentation/mdbook/src/` directory.  Populate the file with references, e.g., 

```sh
@book{knuth1986computer,
  title={The Computer Science of TeX and Metafont: An Inaugural Lecture},
  author={Knuth, Donald E},
  year={1986},
  publisher={American Mathematical Society}
}
```

3. Configure `book.toml`

Tell mdBook to use the `mdbook-bib` preprocessor and specify the path to the
bibliography file in the `book.toml` configuration file.  Add the following section
to the `book.toml`:

```sh
[preprocessor.bib]
# The name of your .bib file, relative to the src directory
bibliography = "bibliography.bib"

# Optional: Set the title for the automatically generated bibliography chapter
title = "Bibliography"

# Optional: Render the entire bibliography ("all") or only cited entries ("cited")
render-bib = "cited"
```

4. Add in-text citations

In a markdown file, use `{{` and `}}` to surround the
citation key, `# cite key`, for example:

`{{` `#cite knuth1986computer` `}}`

5. Build the book

Run the `mdbook build` command.  The preprocessor will automatically run, finding the
citations, generating the citation numbering, and creating a new chapter containing the
formatted bibliography based on the entries in the `.bib` file.

```sh
mdbook build
```
