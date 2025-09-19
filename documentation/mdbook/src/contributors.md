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