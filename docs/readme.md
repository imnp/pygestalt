## Getting set up to develop this documentation locally

Github Pages uses [Jekyll](https://jekyllrb.com/) to convert markdown into HTML using a set of pre-made templates. However it's a pain the the butt to need to push changes to Github, and then wait for Github's servers to flag a change and re-compile the HTML pages.

There's likely many ways to skin the cat, but the path I followed to get this up-and-running on my Mac was [guided by this](http://kbroman.org/simple_site/pages/local_test.html) and approximately:
1. [Install](https://brew.sh/) or [update](https://docs.brew.sh/FAQ) Homebrew. This may be optional, so perhaps skip this and see if needed.
1. [Install RVM \(Ruby Version Manager\)](http://rvm.io/). This should install the latest version of ruby.
1. Type the following code to install github-pages:
	```bash
	gem install github-pages
	```
1. Everything you need to work locally should now be installed. You then navigate to the /docs directory and run:
	```bash
	jekyll serve
	```
1. Open a browser and go [here](http://localhost:4000)

[Here's a a guide to Markdown.](https://guides.github.com/features/mastering-markdown/)
