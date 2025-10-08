# IDE Integration Guide - World-Class Finish Phase 1

This guide provides step-by-step instructions for integrating ruff with your IDE to achieve the tightest possible feedback loop for code quality.

## Visual Studio Code

### 1. Install the Ruff Extension

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Ruff"
4. Install the official "Ruff" extension by Astral Software

### 2. Configure VS Code Settings

Add the following to your VS Code `settings.json`:

```json
{
    // Ruff configuration
    "ruff.enable": true,
    "ruff.organizeImports": true,
    "ruff.fixAll": true,

    // Format on save with ruff
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
        "source.fixAll.ruff": "explicit",
        "source.organizeImports.ruff": "explicit"
    },

    // Python-specific settings
    "[python]": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    }
}
```

### 3. Workspace Settings (Recommended)

Create `.vscode/settings.json` in your project root:

```json
{
    "ruff.enable": true,
    "ruff.organizeImports": true,
    "ruff.fixAll": true,
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
        "source.fixAll.ruff": "explicit",
        "source.organizeImports.ruff": "explicit"
    },
    "[python]": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

## PyCharm / IntelliJ IDEA

### 1. Install Ruff Plugin

1. Go to File → Settings → Plugins
2. Search for "Ruff"
3. Install the "Ruff" plugin
4. Restart PyCharm

### 2. Configure Ruff as External Tool

1. Go to File → Settings → Tools → External Tools
2. Click "+" to add a new tool
3. Configure:
   - **Name**: Ruff Format
   - **Program**: `ruff`
   - **Arguments**: `format $FilePath$`
   - **Working directory**: `$ProjectFileDir$`

4. Add another tool:
   - **Name**: Ruff Check
   - **Program**: `ruff`
   - **Arguments**: `check --fix $FilePath$`
   - **Working directory**: `$ProjectFileDir$`

### 3. Set Up File Watcher (Optional)

1. Go to File → Settings → Tools → File Watchers
2. Add a new watcher:
   - **Name**: Ruff Format
   - **File type**: Python
   - **Scope**: Project Files
   - **Program**: `ruff`
   - **Arguments**: `format $FilePath$`

## Vim/Neovim

### 1. Install with vim-plug

Add to your `.vimrc` or `init.vim`:

```vim
Plug 'astral-sh/ruff-vim'
```

### 2. Configuration

Add to your configuration:

```vim
" Ruff configuration
let g:ruff_autofix = 1
let g:ruff_organize_imports = 1

" Format on save
autocmd BufWritePre *.py :RuffFormat
```

## Emacs

### 1. Install with use-package

```elisp
(use-package ruff-lsp
  :hook (python-mode . ruff-lsp-mode))
```

### 2. Configuration

```elisp
(setq ruff-lsp-server-command '("ruff-lsp"))
```

## Sublime Text

### 1. Install Ruff Package

1. Open Command Palette (Ctrl+Shift+P)
2. Type "Package Control: Install Package"
3. Search for "Ruff"
4. Install the package

### 2. Configuration

Add to your user settings:

```json
{
    "ruff_enable": true,
    "ruff_autofix": true,
    "ruff_organize_imports": true
}
```

## Atom

### 1. Install Ruff Package

1. Go to Settings → Install
2. Search for "linter-ruff"
3. Install the package

### 2. Configuration

The package will automatically use your project's ruff configuration.

## Verification

### Test Your Setup

1. Open a Python file in your IDE
2. Make a formatting change (e.g., add extra spaces)
3. Save the file
4. Verify that ruff automatically formats the code
5. Check that import statements are organized correctly

### Expected Behavior

- **Format on Save**: Code should be automatically formatted when you save
- **Real-time Linting**: Errors should appear as you type
- **Auto-fix**: Many issues should be automatically fixed
- **Import Organization**: Imports should be sorted and organized

## Troubleshooting

### Common Issues

1. **Ruff not found**: Ensure ruff is installed and in your PATH
2. **Format not working**: Check that the ruff extension is enabled
3. **Conflicts with other formatters**: Disable Black, autopep8, or other formatters

### Debug Steps

1. Check ruff installation: `ruff --version`
2. Test ruff manually: `ruff format <file>`
3. Check IDE extension status
4. Review IDE logs for errors

## Performance Benefits

With ruff integration, you'll experience:

- **30x faster** formatting compared to Black
- **Instant** feedback on code quality
- **Automatic** import organization
- **Real-time** error detection
- **Zero** configuration overhead

## Next Steps

After setting up IDE integration:

1. Run `pre-commit install` to enable pre-commit hooks
2. Test the complete workflow: IDE → Pre-commit → CI
3. Enjoy the world-class development experience!

---

**Note**: This guide is part of Phase 1 of the World-Class Finish initiative. The goal is to eliminate subjective debate about code style and establish automated, consistent formatting across the entire development team.
