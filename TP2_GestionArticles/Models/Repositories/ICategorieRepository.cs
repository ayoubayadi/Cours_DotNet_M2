using System.Collections.Generic;
using TP2_GestionArticles.Models; 
namespace TP2_GestionArticles.Models.Repositories
{
    public interface ICategorieRepository
    {
        Category GetById(int Id);
        IList<Category> GetAll();
        void Add(Category t);
        Category Update(Category t);
        void Delete(int Id);
    }
}