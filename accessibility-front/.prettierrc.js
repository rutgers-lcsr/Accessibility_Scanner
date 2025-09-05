import tailwindcssPlugin from 'prettier-plugin-tailwindcss';


const config = {
    htmlWhitespaceSensitivity: 'strict',
    semi: true, // always add semicolons
    singleQuote: true, // use single quotes instead of double
    trailingComma: 'es5', // add trailing commas where valid in ES5
    tabWidth: 4, // 4 spaces per tab
    useTabs: false, // use spaces, not tabs
    printWidth: 100, // wrap lines at 100 chars
    bracketSpacing: true, // add space inside object brackets
    arrowParens: 'always', // always include parens for arrow functions
    endOfLine: 'lf', // enforce LF line endings
    plugins: [tailwindcssPlugin], // if using Tailwind

};

export default config