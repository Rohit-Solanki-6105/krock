// "use client"
import Button from '@/components/button';
import React from 'react';

export default function Home() {
    return (
        <div className="p-8 bg-gray-100 rounded-lg shadow-md mt-4">
            <Button>Hi</Button>
            <h1 className="text-4xl font-bold text-blue-600 mb-4">Home</h1>
            <p className="text-green-400 text-lg">If you can see this, the React routing and Tailwind CSS are perfectly working!</p>
        </div>
    );
}