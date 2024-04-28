document.addEventListener("DOMContentLoaded", function() {
    const blogContainer = document.getElementById('blog');

    // Function to fetch and display markdown files from a specific folder
    async function loadMarkdownPosts() {
        const folderName = 'markdown_posts'; // The folder where your markdown files are located
        const numberOfPosts = 10; // Adjust this number based on your actual number of markdown files
        // Create an array of file paths pointing to the markdown files in the specified folder
        const posts = Array.from({length: numberOfPosts}, (v, k) => `${folderName}/post${k + 1}.md`);

        for (let post of posts) {
            try {
                const response = await fetch(post);
                const text = await response.text();
                const html = marked.parse(text); // Ensure 'marked' library is included in your HTML
                const div = document.createElement('div');
                div.innerHTML = html;
                blogContainer.appendChild(div);
            } catch (error) {
                console.error('Error loading post:', error);
            }
        }
    }

    loadMarkdownPosts();
});
