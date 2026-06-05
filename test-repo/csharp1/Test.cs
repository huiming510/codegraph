using System;
using System.Collections.Generic;

namespace TestProject
{
    public class Person : IComparable<Person>
    {
        public string Name { get; set; }
        public int Age { get; private set; }

        public Person(string name, int age)
        {
            Name = name;
            Age = age;
        }

        public void Greet()
        {
            Console.WriteLine("Hello, {0}!", Name);
        }

        public static bool operator ==(Person left, Person right) => left.Age == right.Age;
        public static bool operator !=(Person left, Person right) => left.Age != right.Age;
    }

    public interface IService
    {
        void Execute();
        string Result { get; }
    }

    public enum Color { Red, Green, Blue }

    public struct Point
    {
        public double X { get; init; }
        public double Y { get; init; }
    }

    public record User(string Name, string Email);

    public class Program
    {
        static void Main(string[] args)
        {
            var p = new Person("Alice", 30);
            p.Greet();

            var list = new List<string>();
            list.Add("test");

            var color = Color.Red;
            if (color == Color.Green)
            {
                Console.WriteLine("Green");
            }

            var point = new Point { X = 1.0, Y = 2.0 };
            Console.WriteLine(point.X);

            var user = new User("Bob", "bob@example.com");
            var svc = new ConsoleService();
            svc.Execute();
        }
    }

    public class ConsoleService : IService
    {
        public void Execute()
        {
            Console.WriteLine("Done");
        }

        public string Result => "OK";
    }
}
