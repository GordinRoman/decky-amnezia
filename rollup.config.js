import commonjs from "@rollup/plugin-commonjs";
import resolve from "@rollup/plugin-node-resolve";
import replace from "@rollup/plugin-replace";
import typescript from "@rollup/plugin-typescript";

export default {
  input: "src/index.tsx",
  plugins: [
    commonjs(),
    resolve(),
    replace({
      preventAssignment: false,
      "process.env.NODE_ENV": JSON.stringify("production"),
    }),
    typescript(),
  ],
  external: ["react", "react-dom", "decky-frontend-lib"],
  // react-icons' transpiled CJS uses `this` as a global fallback; in ESM
  // bundle scope `this` is undefined, which is correct — the library has
  // a runtime fallback. Silence the noisy warning.
  onwarn(warning, warn) {
    if (warning.code === "THIS_IS_UNDEFINED") return;
    warn(warning);
  },
  output: {
    file: "dist/index.js",
    name: "AmneziaWG",
    globals: {
      react: "SP_REACT",
      "react-dom": "SP_REACTDOM",
      "decky-frontend-lib": "DFL",
    },
    format: "iife",
    exports: "default",
  },
};
