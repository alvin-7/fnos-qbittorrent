import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'tests',timeout:20000,use:{launchOptions:{executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']},screenshot:'only-on-failure'},reporter:[['list'],['json',{outputFile:'evidence/browser-results.json'}]]});
