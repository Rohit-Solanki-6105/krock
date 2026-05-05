import React, { useState, useEffect } from "react";
import TodoItem, { Todo } from "./components/TodoItem";

export default function Todos() {
    const [todos, setTodos] = useState<Todo[]>([]);
    const [title, setTitle] = useState("");
    const [loading, setLoading] = useState(true);

    const fetchTodos = async () => {
        try {
            const res = await fetch("/api/todos");
            const data = await res.json();
            if (Array.isArray(data)) {
                setTodos(data);
            }
        } catch (error) {
            console.error("Failed to fetch todos", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTodos();
    }, []);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;

        try {
            const res = await fetch("/api/todos", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: title.trim() })
            });
            const newTodo = await res.json();
            if (!newTodo.error) {
                setTodos([newTodo, ...todos]);
                setTitle("");
            }
        } catch (error) {
            console.error("Failed to add todo", error);
        }
    };

    const handleToggle = async (todo: Todo) => {
        // Optimistic update
        setTodos(todos.map(t => t.id === todo.id ? { ...t, completed: !t.completed } : t));
        
        try {
            await fetch("/api/todos", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: todo.id, completed: !todo.completed })
            });
        } catch (error) {
            // Revert on failure
            setTodos(todos.map(t => t.id === todo.id ? { ...t, completed: todo.completed } : t));
            console.error("Failed to update todo", error);
        }
    };

    const handleDelete = async (id: number) => {
        // Optimistic update
        const previousTodos = [...todos];
        setTodos(todos.filter(t => t.id !== id));
        
        try {
            await fetch("/api/todos", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id })
            });
        } catch (error) {
            // Revert on failure
            setTodos(previousTodos);
            console.error("Failed to delete todo", error);
        }
    };

    return (
        <div className="max-w-2xl mx-auto p-6 bg-gray-50 min-h-[500px] rounded-xl shadow-lg mt-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-8 text-center">My Tasks</h1>
            
            <form onSubmit={handleAdd} className="flex gap-2 mb-8">
                <input 
                    type="text" 
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="What needs to be done?"
                    className="flex-1 p-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
                />
                <button 
                    type="submit"
                    disabled={!title.trim()}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Add Task
                </button>
            </form>

            {loading ? (
                <div className="flex justify-center p-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            ) : todos.length === 0 ? (
                <div className="text-center p-8 text-gray-500">
                    <p className="text-lg">No tasks yet. Add one above!</p>
                </div>
            ) : (
                <ul className="space-y-2">
                    {todos.map(todo => (
                        <TodoItem 
                            key={todo.id} 
                            todo={todo} 
                            onToggle={handleToggle} 
                            onDelete={handleDelete} 
                        />
                    ))}
                </ul>
            )}
        </div>
    );
}
