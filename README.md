
---

# Omar ABEDELKADER's webiste

Welcome to my personal website! This website was built using a modified version of the Academic Pages GitHub template.

## Getting Started

To explore the website, you can visit the live version at: **[https://omarabedelkader.github.io](https://omarabedelkader.github.io)**.

### Features:
- Academic-style pages for organizing and displaying research, projects, and other professional content.
- Easy-to-navigate structure with links to various sections, including publications, projects, and more.
- Support for adding PDFs, downloadable files, and other resources.

## How to Use This Website

- To view content, browse through the sections available in the navigation bar.
- Any downloadable files, such as PDFs, can be accessed in the "Files" section or directly at: **https://omarabedelkader.github.io/files/example.pdf**.

## Running Locally

To preview changes or run the website locally:

1. **Clone the repository** and make updates to the content.
   
2. **Install dependencies**:
   - On Linux or Windows Subsystem for Linux (WSL):
     ```bash
     sudo apt install ruby-dev ruby-bundler nodejs
     ```
   - On macOS:
     ```bash
     brew install ruby
     brew install node
     gem install bundler
     ```

3. **Install Ruby dependencies** by running:
   ```bash
   bundle install
   ```
   If there are errors, delete the `Gemfile.lock` and try again.

4. **Serve the website locally** by running:
   ```bash
   jekyll serve -l -H localhost
   ```
   Access the local version at **http://localhost:4000**. The local server will automatically rebuild and refresh on any changes.

### Additional Dependencies (Linux)

If you are running on Linux, you may need to install additional dependencies:
```bash
sudo apt install build-essential gcc make
```

## Maintenance

For questions, issues, or feature requests related to this website, feel free to reach out via the contact information provided on the site.

## Credits

This website was built using a modified version of the **Academic Pages** template, originally created by [Stuart Geiger](https://github.com/staeiou) and maintained by [Robert Zupko](https://github.com/rgzupko). The template is based on the **Minimal Mistakes Jekyll Theme**, © 2016 [Michael Rose](https://github.com/mmistakes), released under the MIT License.

