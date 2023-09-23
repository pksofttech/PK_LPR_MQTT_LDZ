/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./templates/**/*.{html,js}"],
    plugins: [
        // include Flowbite as a plugin in your Tailwind CSS project
        require("daisyui"),
    ],
    daisyui: {
        themes: [
            {
                apptheme: {
                    primary: "#31bf7a",

                    secondary: "#f78c65",

                    accent: "#f9bbec",

                    neutral: "#392c3a",

                    "base-100": "#37313a",

                    info: "#96d7f8",

                    success: "#18774c",

                    warning: "#fab92e",

                    error: "#e64c47",
                },
            },
        ], // true: all themes | false: only light + dark | array: specific themes like this ["light", "dark", "cupcake"]
        darkTheme: "dark", // name of one of the included themes for dark mode
        base: true, // applies background color and foreground color for root element by default
        styled: true, // include daisyUI colors and design decisions for all components
        utils: true, // adds responsive and modifier utility classes
        rtl: false, // rotate style direction from left-to-right to right-to-left. You also need to add dir="rtl" to your html tag and install `tailwindcss-flip` plugin for Tailwind CSS.
        prefix: "", // prefix for daisyUI classnames (components, modifiers and responsive class names. Not colors)
        logs: true, // Shows info about daisyUI version and used config in the console when building your CSS
    },
};
