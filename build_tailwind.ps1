# Install Tailwind CSS if not already installed
if (!(Test-Path -Path "node_modules/.bin/tailwind")) {
    npm install -D tailwindcss postcss autoprefixer
}

# Build Tailwind CSS
& npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/tailwind.css --minify
