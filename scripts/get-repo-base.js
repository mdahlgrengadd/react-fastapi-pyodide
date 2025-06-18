// Script to get the repository name for GitHub Pages preview
const repo = process.env.GITHUB_REPOSITORY?.split('/')[1] || 'react-router-fastapi';
console.log(`/${repo}/`);
