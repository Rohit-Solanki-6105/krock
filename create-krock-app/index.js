#!/usr/bin/env node

import { Command } from 'commander';
import inquirer from 'inquirer';
import { execa } from 'execa';
import chalk from 'chalk';
import ora from 'ora';
import path from 'path';
import fs from 'fs-extra';

const program = new Command();
const REPO_URL = 'https://github.com/Rohit-Solanki-6105/krock.git';

program
    .name('create-krock-app')
    .description('Bootstrap a new Krock project from GitHub')
    .argument('[project-name]', 'Name of the project directory')
    .action(async (projectName) => {

        // 1. Determine Project Name
        let targetDir = projectName;
        if (!targetDir || targetDir === '.') {
            const answers = await inquirer.prompt([
                {
                    type: 'input',
                    name: 'name',
                    message: 'What is your project name?',
                    default: 'my-krock-app',
                },
            ]);
            targetDir = answers.name;
        }

        const projectPath = path.resolve(process.cwd(), targetDir);

        // Prevent overwriting existing non-empty folders
        if (fs.existsSync(projectPath) && fs.readdirSync(projectPath).length > 0) {
            console.error(chalk.red(`\nDirectory ${targetDir} already exists and is not empty.`));
            process.exit(1);
        }

        try {
            // 2. Clone the Repository
            const cloneSpinner = ora(`Cloning Krock template from GitHub...`).start();
            await execa('git', ['clone', REPO_URL, targetDir]);

            // Remove the .git folder so it's a fresh project
            await fs.remove(path.join(projectPath, '.git'));
            cloneSpinner.succeed(chalk.green('Template cloned successfully.'));

            // 3. Check for Python
            const pythonBusy = ora('Checking for Python...').start();
            let pythonCmd = 'python';
            try {
                await execa('python', ['--version']);
            } catch {
                try {
                    await execa('python3', ['--version']);
                    pythonCmd = 'python3';
                } catch {
                    pythonBusy.fail('Python not found. Please install Python to continue.');
                    process.exit(1);
                }
            }
            pythonBusy.succeed(chalk.green('Python detected.'));

            // 4. Ask for Virtual Environment Name
            const venvAnswers = await inquirer.prompt([
                {
                    type: 'input',
                    name: 'venvName',
                    message: 'What should we name the Python virtual environment?',
                    default: 'venv',
                },
            ]);
            const venvName = venvAnswers.venvName;

            // 5. Create Virtual Environment
            const venvSpinner = ora(`Creating venv: ${venvName}...`).start();
            await execa(pythonCmd, ['-m', 'venv', venvName], { cwd: projectPath });
            venvSpinner.succeed(chalk.green(`Virtual environment created.`));

            // 6. Install Python Requirements
            const reqPath = path.join(projectPath, 'requirements.txt');
            if (fs.existsSync(reqPath)) {
                const pipSpinner = ora('Installing Python dependencies...').start();
                const pipPath = process.platform === 'win32'
                    ? path.join(projectPath, venvName, 'Scripts', 'pip')
                    : path.join(projectPath, venvName, 'bin', 'pip');

                await execa(pipPath, ['install', '-r', 'requirements.txt'], { cwd: projectPath });
                pipSpinner.succeed(chalk.green('Python requirements installed.'));
            }

            // 7. NPM Install
            if (fs.existsSync(path.join(projectPath, 'package.json'))) {
                const npmSpinner = ora('Installing Node dependencies...').start();
                await execa('npm', ['install'], { cwd: projectPath });
                npmSpinner.succeed(chalk.green('Node dependencies installed.'));
            }

            // Final Instructions
            console.log(`\n${chalk.bgCyan.black(' DONE ')} ${chalk.green('Project initialized successfully!')}`);
            console.log(`\n${chalk.bold('Next steps:')}`);
            console.log(chalk.cyan(`  cd ${targetDir}`));
            if (process.platform === 'win32') {
                console.log(chalk.cyan(`  ${venvName}\\Scripts\\activate`));
            } else {
                console.log(chalk.cyan(`  source ${venvName}/bin/activate`));
            }
            console.log(chalk.cyan(`  npm run dev (or your start command)`));

        } catch (error) {
            console.error(chalk.red('\nSetup failed:'), error.message);
            process.exit(1);
        }
    });

program.parse(process.argv);